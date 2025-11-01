"""Plugin loader and sandbox helpers for Chaos Keyboard effects."""
from __future__ import annotations

import builtins
import importlib.util
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Callable, Iterable, Iterator, Sequence

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
            flag_value = os.environ.get(self.developer_flag, "")
            self.developer_mode = flag_value.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
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
            root = name.split(".", 1)[0]
            if root in blocked:
                raise ImportError(
                    (
                        f"Import of '{root}' is disabled for Chaos Keyboard plugins. "
                        f"Set {flag_name}=1 to opt into developer mode."
                    )
                )
            return original_import(name, globals, locals, fromlist, level)

        builtins.__import__ = sandboxed_import
        try:
            yield
        finally:
            builtins.__import__ = original_import


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

    try:
        with sandbox.guard_imports():
            spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


if TYPE_CHECKING:  # pragma: no cover - hint only
    from . import EffectFactory, EffectRegistry
