"""Plugin loader and sandbox helpers for Chaos Keyboard effects."""
from __future__ import annotations

import builtins
import importlib.util
import os
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Callable, ClassVar, Iterable, Iterator, Sequence

__all__ = [
    "PluginApp",
    "PluginLoadError",
    "PluginSandbox",
    "load_effect_plugins",
]


class PluginLoadError(RuntimeError):
    """Raised when a plugin cannot be imported or registered successfully."""


@dataclass(slots=True)
class PluginSandbox:
    """Restrict plugin imports to the simulation-safe subset of the stdlib."""

    developer_mode: bool | None = None
    blocked_modules: Iterable[str] = frozenset({"subprocess", "socket", "ctypes"})
    developer_flag: str = "CHAOS_KEYBOARD_ALLOW_UNSAFE_PLUGINS"

    def __post_init__(self) -> None:
        if self.developer_mode is None:
            self.developer_mode = self._developer_flag_is_set()
        self.blocked_modules = frozenset(self.blocked_modules)

    @property
    def developer_mode_enabled(self) -> bool:
        """Return ``True`` when sandbox restrictions are lifted for developers."""

        return bool(self.developer_mode)

    @contextmanager
    def guard_imports(self) -> Iterator[None]:
        """Temporarily wrap ``__import__`` to block dangerous modules."""

        if self.developer_mode_enabled:
            yield
            return

        self._install_import_guard()
        try:
            yield
        finally:
            self._release_import_guard()

    def bind_module_imports(self, module: ModuleType) -> None:
        """Ensure a plugin module retains the sandboxed ``__import__``."""

        if self.developer_mode_enabled:
            return

        import_function = self._ensure_import_function()

        builtins_obj = module.__dict__.get("__builtins__")
        if isinstance(builtins_obj, dict):
            sandboxed_builtins = dict(builtins_obj)
        elif builtins_obj is None:
            sandboxed_builtins = dict(vars(builtins))
        else:
            sandboxed_builtins = dict(vars(builtins_obj))
        sandboxed_builtins["__import__"] = import_function
        module.__dict__["__builtins__"] = sandboxed_builtins
        module_name = module.__dict__.get("__name__")
        if isinstance(module_name, str):
            self._sandboxed_modules.add(module_name)

    def activate_persistent_guard(self) -> None:
        """Keep the sandbox import guard active for the plugin lifetime."""

        if self.developer_mode_enabled or self._persistent_guard:
            return
        self._install_import_guard()
        self._persistent_guard = True

    def register_plugin_root(self, root: Path) -> Path | None:
        """Remember the plugin's filesystem root for call-site detection."""

        if self.developer_mode_enabled:
            return None

        resolved = root.resolve()
        self._sandbox_roots.add(resolved)
        return resolved

    def unregister_plugin_root(self, root: Path) -> None:
        """Remove a plugin root after a failed import."""

        self._sandbox_roots.discard(root)

    def track_module_name(self, module_name: str) -> None:
        """Record plugin module names that should remain sandboxed."""

        if self.developer_mode_enabled:
            return

        self._sandboxed_modules.add(module_name)

    def untrack_module_name(self, module_name: str) -> None:
        """Remove a module from sandbox tracking after a failed import."""

        self._sandboxed_modules.discard(module_name)

    def _ensure_import_function(self) -> Callable[..., ModuleType]:
        if self._sandboxed_import is None:
            original_import = builtins.__import__
            blocked = self.blocked_modules
            flag_name = self.developer_flag

            def sandboxed_import(
                name: str,
                globals: dict[str, object] | None = None,
                locals: dict[str, object] | None = None,
                fromlist: Sequence[str] = (),
                level: int = 0,
            ) -> ModuleType:
                if self.developer_mode_enabled:
                    return original_import(name, globals, locals, fromlist, level)

                if self._should_enforce_for_call(globals):
                    root = name.split(".", 1)[0]
                    if root in blocked:
                        raise ImportError(
                            (
                                f"Import of '{root}' is disabled for Chaos Keyboard plugins. "
                                f"Set {flag_name}=1 to opt into developer mode."
                            )
                        )

                return original_import(name, globals, locals, fromlist, level)

            self._sandboxed_import = sandboxed_import
        return self._sandboxed_import

    def _install_import_guard(self) -> None:
        if self.developer_mode_enabled:
            return
        if self._guard_depth == 0:
            self._original_import = builtins.__import__
            builtins.__import__ = self._ensure_import_function()
        self._guard_depth += 1

    def _release_import_guard(self) -> None:
        if self.developer_mode_enabled or self._guard_depth == 0:
            return
        if self._persistent_guard and self._guard_depth == 1:
            return
        self._guard_depth -= 1
        if self._guard_depth == 0 and self._original_import is not None:
            builtins.__import__ = self._original_import
            self._original_import = None

    def _developer_flag_is_set(self) -> bool:
        flag_value = os.environ.get(self.developer_flag, "")
        return flag_value.strip().lower() in self._TRUTHY_VALUES

    def _should_enforce_for_call(
        self, globals_dict: dict[str, object] | None
    ) -> bool:
        # Reentrancy guard: _is_sandbox_path may trigger imports (e.g.
        # ``os.path`` internals) that re-enter the sandboxed import hook.
        # While we are already deciding whether to enforce, skip the check
        # to avoid infinite recursion.  Uses thread-local storage so
        # concurrent threads are handled independently.
        if getattr(self._thread_local, "in_check", False):
            return False
        self._thread_local.in_check = True
        try:
            return self._check_enforcement(globals_dict)
        finally:
            self._thread_local.in_check = False

    def _check_enforcement(
        self, globals_dict: dict[str, object] | None
    ) -> bool:
        if globals_dict:
            module_name = globals_dict.get("__name__")
            if isinstance(module_name, str) and module_name in self._sandboxed_modules:
                return True
            module_file = globals_dict.get("__file__")
            if isinstance(module_file, str) and self._is_sandbox_path(module_file):
                return True

        try:
            frame = sys._getframe(2)
        except ValueError:
            return False
        while frame:
            module_name = frame.f_globals.get("__name__")
            if isinstance(module_name, str) and module_name in self._sandboxed_modules:
                return True
            module_file = frame.f_globals.get("__file__")
            if isinstance(module_file, str) and self._is_sandbox_path(module_file):
                return True
            frame = frame.f_back

        return False

    def _is_sandbox_path(self, file_path: str) -> bool:
        candidate = os.path.realpath(file_path)
        for root in self._sandbox_roots:
            root_str = self._resolved_root_strings.get(root)
            if root_str is None:
                root_str = os.path.realpath(str(root))
                self._resolved_root_strings[root] = root_str
            if candidate == root_str or candidate.startswith(root_str + os.sep):
                return True
        return False

    _original_import: Callable[..., ModuleType] | None = field(default=None, init=False, repr=False)
    _sandboxed_import: Callable[..., ModuleType] | None = field(
        default=None, init=False, repr=False
    )
    _guard_depth: int = field(default=0, init=False, repr=False)
    _persistent_guard: bool = field(default=False, init=False, repr=False)
    _sandboxed_modules: set[str] = field(default_factory=set, init=False, repr=False)
    _sandbox_roots: set[Path] = field(default_factory=set, init=False, repr=False)
    _thread_local: threading.local = field(default_factory=threading.local, init=False, repr=False)
    _resolved_root_strings: dict[Path, str] = field(default_factory=dict, init=False, repr=False)
    _TRUTHY_VALUES: ClassVar[frozenset[str]] = frozenset({"1", "true", "yes", "on"})


@dataclass(slots=True)
class PluginApp:
    """Context object handed to plugins during registration."""

    registry: "EffectRegistry"
    sandbox: PluginSandbox

    def register_factory(
        self,
        name: str,
        factory: "EffectFactory",
        *,
        capabilities: Iterable[str] | None = None,
    ) -> None:
        """Register an effect factory directly with the target registry."""

        self.registry.register(name, factory, capabilities=capabilities)

    def register_effect(
        self,
        name: str,
        *,
        capabilities: Iterable[str] | None = None,
    ) -> Callable[["EffectFactory"], "EffectFactory"]:
        """Return a decorator mirroring :func:`chaos_keyboard.effects.register_effect`."""

        def decorator(factory: "EffectFactory") -> "EffectFactory":
            self.register_factory(name, factory, capabilities=capabilities)
            return factory

        return decorator

    @property
    def developer_mode_enabled(self) -> bool:
        """Expose the sandbox flag so plugins can offer gated capabilities."""

        return self.sandbox.developer_mode_enabled


def load_effect_plugins(
    *,
    base_path: Path | str | None = None,
    registry: "EffectRegistry" | None = None,
    sandbox: PluginSandbox | None = None,
) -> tuple[str, ...]:
    """Discover and load plugin ``effect.py`` modules found under ``effects/``."""

    from . import EffectRegistry  # Local import avoids circular during module load.

    target_registry: EffectRegistry
    if registry is None:
        from . import registry as global_registry

        target_registry = global_registry
    else:
        target_registry = registry

    sandbox = sandbox or PluginSandbox()
    app = PluginApp(registry=target_registry, sandbox=sandbox)

    root = Path(base_path) if base_path is not None else Path(__file__).resolve().parent
    if not root.exists():
        return tuple()

    namespace = _ensure_namespace(root)

    loaded: list[str] = []
    for candidate in sorted(p for p in root.iterdir() if p.is_dir()):
        if candidate.name == "__pycache__":
            continue
        module_path = candidate / "effect.py"
        if not module_path.is_file():
            continue
        package_name = f"{namespace}.{candidate.name}"
        module_name = f"{package_name}.effect"
        try:
            module = _load_plugin_module(module_name, module_path, candidate, sandbox)
        except Exception as exc:  # pragma: no cover - defensive; handled below.
            raise PluginLoadError(
                f"Failed to import plugin '{candidate.name}': {exc}"
            ) from exc
        register = getattr(module, "register", None)
        if not callable(register):
            raise PluginLoadError(
                f"Plugin '{candidate.name}' does not define register(app)."
            )
        try:
            with sandbox.guard_imports():
                register(app)
        except Exception as exc:  # pragma: no cover - surfaced to caller.
            raise PluginLoadError(
                f"Plugin '{candidate.name}' raised during registration: {exc}"
            ) from exc
        loaded.append(candidate.name)
    return tuple(loaded)


def _ensure_namespace(root: Path) -> str:
    """Ensure the in-memory namespace package for dynamic plugins exists."""

    namespace = "chaos_keyboard.effects._plugins"
    package = sys.modules.get(namespace)
    if package is None:
        package = ModuleType(namespace)
        package.__path__ = [str(root)]  # type: ignore[attr-defined]
        sys.modules[namespace] = package
    else:
        search_locations = getattr(package, "__path__", None)
        if isinstance(search_locations, list) and str(root) not in search_locations:
            search_locations.append(str(root))
    return namespace


def _load_plugin_module(
    module_name: str,
    module_path: Path,
    package_path: Path,
    sandbox: PluginSandbox,
) -> ModuleType:
    """Import a plugin module under the synthetic namespace package."""

    package_name = module_name.rpartition(".")[0]
    package = sys.modules.get(package_name)
    if package is None:
        package = ModuleType(package_name)
        package.__path__ = [str(package_path)]  # type: ignore[attr-defined]
        sys.modules[package_name] = package
    else:
        search_locations = getattr(package, "__path__", None)
        if isinstance(search_locations, list) and str(package_path) not in search_locations:
            search_locations.append(str(package_path))

    spec = importlib.util.spec_from_file_location(
        module_name,
        module_path,
        submodule_search_locations=[str(package_path)],
    )
    if spec is None or spec.loader is None:
        raise PluginLoadError(
            f"Unable to create a module spec for plugin '{module_name}'."
        )

    module = sys.modules.get(module_name)
    if module is None:
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module

    registered_root = sandbox.register_plugin_root(package_path)
    sandbox.track_module_name(module_name)

    try:
        with sandbox.guard_imports():
            spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        sandbox.untrack_module_name(module_name)
        if registered_root is not None:
            sandbox.unregister_plugin_root(registered_root)
        raise
    else:
        sandbox.bind_module_imports(module)
        sandbox.activate_persistent_guard()
    return module


if TYPE_CHECKING:  # pragma: no cover - hint only
    from . import EffectFactory, EffectRegistry
