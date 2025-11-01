from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import pytest

from chaos_keyboard.bus import EventBus, SystemAction
from chaos_keyboard.config import load_profiles, select_profile
from chaos_keyboard.safety import SafetyContext


@pytest.fixture(autouse=True)
def textual_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    textual = types.ModuleType("textual")

    app_module = types.ModuleType("textual.app")

    class _App:
        BINDINGS = []

        def __init__(self, *args, **kwargs) -> None:  # noqa: D401 - stub
            pass

        def run(self) -> int:
            return 0

        def exit(self) -> None:
            pass

    app_module.App = _App
    app_module.ComposeResult = list

    widgets_module = types.ModuleType("textual.widgets")

    class _Static:
        def __init__(self, text: str = "", *, id: str | None = None) -> None:
            self.text = text
            self.id = id

        def update(self, text: str) -> None:
            self.text = text

    class _Checkbox:
        class Changed:
            def __init__(self, checkbox: "_Checkbox", value: bool) -> None:
                self.checkbox = checkbox
                self.value = value

        def __init__(self, label: str, value: bool = False, *, id: str | None = None) -> None:
            self.label = label
            self.value = value
            self.id = id

    class _Button:
        class Pressed:
            def __init__(self, button: _Button) -> None:
                self.button = button
                self._stopped = False

            def stop(self) -> None:
                self._stopped = True

        def __init__(self, label: str, *, id: str | None = None) -> None:
            self.label = label
            self.id = id

    class _Header:
        def __init__(self, *args, **kwargs) -> None:
            pass

    class _Footer:
        def __init__(self, *args, **kwargs) -> None:
            pass

    widgets_module.Static = _Static
    widgets_module.Checkbox = _Checkbox
    widgets_module.Button = _Button
    widgets_module.Header = _Header
    widgets_module.Footer = _Footer

    modules = {
        "textual": textual,
        "textual.app": app_module,
        "textual.widgets": widgets_module,
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    yield
    for name in modules:
        monkeypatch.delitem(sys.modules, name, raising=False)


@dataclass
class DummyEffectController:
    started: list[tuple[str, str | None]]
    stopped: list[str]

    def __init__(self) -> None:
        self.started = []
        self.stopped = []

    def start_effect(self, name: str, *, source: str | None = None) -> None:
        self.started.append((name, source))

    def stop_effect(self, name: str) -> None:
        self.stopped.append(name)

    def close(self) -> None:
        pass


def test_tui_effect_toggle_updates_controller_and_stats() -> None:
    from chaos_keyboard.tui import ChaosKeyboardTUI

    profile = select_profile(None, load_profiles())
    bus = EventBus()
    safety = SafetyContext(profile.safety.mode)
    controller = DummyEffectController()

    app = ChaosKeyboardTUI(
        profile,
        bus=bus,
        safety=safety,
        effect_controller=controller,
        telemetry=None,
    )

    app.simulate_toggle("fake_bsod", True)
    assert controller.started == [("fake_bsod", "tui")]
    bus.publish(SystemAction(name="effect_started", payload={"effect": "fake_bsod"}))
    assert app.stats()["active_effects"] == 1

    app.simulate_toggle("fake_bsod", False)
    assert controller.stopped == ["fake_bsod"]
    bus.publish(SystemAction(name="effect_stopped", payload={"effect": "fake_bsod"}))
    assert app.stats()["active_effects"] == 0

    app.teardown()
