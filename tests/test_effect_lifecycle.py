"""Lifecycle tests for built-in Chaos Keyboard effects."""
from __future__ import annotations

import pytest

from chaos_keyboard.bus import EventBus, SystemAction, VisualAction
from chaos_keyboard.effects import EffectController, register_effect, registry
from chaos_keyboard.safety import CapabilityNotAllowed, SafetyContext, SIM_ONLY


@pytest.fixture()
def controller() -> tuple[EffectController, EventBus, SafetyContext]:
    bus = EventBus()
    context = SafetyContext(mode=SIM_ONLY)
    ctrl = EffectController(context, bus)
    return ctrl, bus, context


def test_fake_bsod_toggle(controller: tuple[EffectController, EventBus, SafetyContext]) -> None:
    ctrl, bus, _ = controller
    ctrl.bind_key("F1", "fake_bsod")

    visuals: list[VisualAction] = []
    bus.subscribe(VisualAction, visuals.append)

    bus.publish(SystemAction(name="key_press", payload={"text": "F1"}))
    assert "fake_bsod" in ctrl.active_effects
    assert any("Fake BSOD" in action.description for action in visuals)

    bus.publish(SystemAction(name="key_press", payload={"text": "F1"}))
    assert "fake_bsod" not in ctrl.active_effects
    assert any("dismissed" in action.description for action in visuals)


def test_capability_enforcement_blocks_system_effect(
    controller: tuple[EffectController, EventBus, SafetyContext]
) -> None:
    ctrl, _, _ = controller

    @register_effect("restricted_system", capabilities={"system"})
    def _factory(context: SafetyContext, bus: EventBus):  # type: ignore[override]
        class RestrictedEffect:
            name = "restricted_system"
            capabilities = frozenset({"system"})

            def __init__(self) -> None:
                self._active = False

            def start(self) -> None:
                self._active = True

            def stop(self) -> None:
                self._active = False

            def status(self) -> str:
                return "running" if self._active else "idle"

        return RestrictedEffect()

    try:
        with pytest.raises(CapabilityNotAllowed):
            ctrl.start_effect("restricted_system")
        assert "restricted_system" not in ctrl.active_effects
    finally:
        registry.unregister("restricted_system")


def test_mock_keylogger_captures_keystrokes(
    controller: tuple[EffectController, EventBus, SafetyContext]
) -> None:
    ctrl, bus, _ = controller
    ctrl.bind_key("F5", "mock_keylogger")

    bus.publish(SystemAction(name="key_press", payload={"text": "F5"}))
    assert "mock_keylogger" in ctrl.active_effects

    bus.publish(SystemAction(name="key_press", payload={"text": "h"}))
    bus.publish(SystemAction(name="key_press", payload={"text": "i"}))

    # Stop the effect to read its status snapshot
    bus.publish(SystemAction(name="key_press", payload={"text": "F5"}))
    effect = ctrl.get_effect("mock_keylogger")
    assert effect is not None
    assert "hi" in effect.status()

    # Additional keypresses after stop must not be captured.
    bus.publish(SystemAction(name="key_press", payload={"text": "!"}))
    assert "!" not in effect.status()


def test_panic_stops_all_effects(
    controller: tuple[EffectController, EventBus, SafetyContext]
) -> None:
    ctrl, bus, context = controller
    ctrl.bind_key("F1", "fake_bsod")
    bus.publish(SystemAction(name="key_press", payload={"text": "F1"}))
    assert ctrl.active_effects

    context.panic()
    assert not ctrl.active_effects
