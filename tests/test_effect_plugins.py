"""Tests covering the plugin loader and sandbox enforcement."""
from __future__ import annotations

from pathlib import Path

import pytest

from chaos_keyboard.bus import EventBus
from chaos_keyboard.effects import EffectController, EffectRegistry
from chaos_keyboard.effects.plugins import (
    PluginLoadError,
    PluginSandbox,
    load_effect_plugins,
)
from chaos_keyboard.safety import CapabilityNotAllowed, SafetyContext, SIM_ONLY


@pytest.fixture()
def plugin_registry(monkeypatch: pytest.MonkeyPatch) -> EffectRegistry:
    """Provide an isolated effect registry for plugin tests."""

    import chaos_keyboard.effects as effects_module

    registry = EffectRegistry(_factories={}, _capabilities={})
    monkeypatch.setattr(effects_module, "registry", registry)
    return registry


@pytest.fixture()
def sample_plugin_root() -> Path:
    """Return the path containing checked-in sample plugins."""

    return Path(__file__).with_name("sample_plugins")


@pytest.fixture()
def loaded_sample_plugins(
    plugin_registry: EffectRegistry, sample_plugin_root: Path
) -> EffectRegistry:
    """Load bundled sample plugins into the isolated registry."""

    load_effect_plugins(base_path=sample_plugin_root, registry=plugin_registry)
    return plugin_registry


def test_plugin_loader_registers_decorator_plugin(
    loaded_sample_plugins: EffectRegistry,
) -> None:
    effect = loaded_sample_plugins.load(
        "decorator_demo", SafetyContext(mode=SIM_ONLY), EventBus()
    )
    assert effect.status() == "idle"
    effect.start()
    assert effect.status() == "running"


def test_plugin_capability_enforced_by_safety(
    loaded_sample_plugins: EffectRegistry,
) -> None:
    controller = EffectController(SafetyContext(mode=SIM_ONLY), EventBus())
    with pytest.raises(CapabilityNotAllowed):
        controller.start_effect("network_probe")


def test_sandbox_blocks_subprocess_import(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "unsafe"
    plugin_dir.mkdir()
    (plugin_dir / "effect.py").write_text(
        """
from __future__ import annotations

import subprocess


def register(app) -> None:
    raise AssertionError("should not be reached when sandbox works")
"""
    )
    registry = EffectRegistry(_factories={}, _capabilities={})
    sandbox = PluginSandbox(developer_mode=False)
    with pytest.raises(PluginLoadError):
        load_effect_plugins(base_path=tmp_path, registry=registry, sandbox=sandbox)


def test_developer_flag_allows_blocked_modules(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CHAOS_KEYBOARD_ALLOW_UNSAFE_PLUGINS", "1")
    plugin_dir = tmp_path / "devmode"
    plugin_dir.mkdir()
    (plugin_dir / "effect.py").write_text(
        """
from __future__ import annotations

import subprocess


class UnsafeDemo:
    name = "unsafe_demo"
    capabilities = frozenset({"ui"})

    def __init__(self, context, bus) -> None:
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def status(self) -> str:
        return "running" if self._running else "idle"


def register(app) -> None:
    app.register_factory(
        "unsafe_demo",
        lambda context, bus: UnsafeDemo(context, bus),
        capabilities=UnsafeDemo.capabilities,
    )
"""
    )
    registry = EffectRegistry(_factories={}, _capabilities={})
    sandbox = PluginSandbox()
    loaded = load_effect_plugins(base_path=tmp_path, registry=registry, sandbox=sandbox)
    assert loaded == ("devmode",)
    effect = registry.load("unsafe_demo", SafetyContext(mode=SIM_ONLY), EventBus())
    assert effect.status() == "idle"
