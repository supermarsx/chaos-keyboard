"""Lifecycle tests for built-in Chaos Keyboard effects."""
from __future__ import annotations

from dataclasses import dataclass

import pytest

from chaos_keyboard.bus import EventBus, SystemAction, VisualAction
from chaos_keyboard.effects import EffectController, register_effect, registry
from chaos_keyboard.safety import (
    CapabilityNotAllowed,
    InterlockPending,
    SafetyContext,
    SafetyInterlocks,
    SIM_ONLY,
)


@dataclass(frozen=True)
class EffectExpectation:
    """Describe the expected behaviour of a simulation-only effect."""

    name: str
    capabilities: frozenset[str] | set[str]
    start_visual_contains: str
    stop_visual_contains: str
    start_system: tuple[str, str] | tuple[str, None] | None = None
    stop_system: tuple[str, str] | tuple[str, None] | None = None


EFFECT_CASES = (
    EffectExpectation(
        name="force_close",
        capabilities={"ui"},
        start_visual_contains="Force-close routine engaged",
        stop_visual_contains="Demo apps reopened",
        start_system=("demo_app_control", "close"),
        stop_system=("demo_app_control", "restore"),
    ),
    EffectExpectation(
        name="fake_exfil",
        capabilities={"ui"},
        start_visual_contains="Fake exfiltration initiated",
        stop_visual_contains="Fake exfiltration cancelled",
        start_system=("fake_exfiltration", "begin"),
        stop_system=("fake_exfiltration", "complete"),
    ),
    EffectExpectation(
        name="key_swap",
        capabilities={"ui"},
        start_visual_contains="Key swap chaos enabled",
        stop_visual_contains="Key swap disabled",
        start_system=("input_mutation", "swap"),
        stop_system=("input_mutation", "restore"),
    ),
    EffectExpectation(
        name="invert_screen",
        capabilities={"overlay"},
        start_visual_contains="Invert screen shader enabled",
        stop_visual_contains="Invert screen shader disabled",
    ),
    EffectExpectation(
        name="high_contrast",
        capabilities={"ui"},
        start_visual_contains="High contrast theme activated",
        stop_visual_contains="High contrast theme restored",
    ),
    EffectExpectation(
        name="mouse_gremlin",
        capabilities={"ui"},
        start_visual_contains="Mouse gremlin released",
        stop_visual_contains="Mouse gremlin contained",
        start_system=("pointer_gremlin", "start"),
        stop_system=("pointer_gremlin", "stop"),
    ),
    EffectExpectation(
        name="matrix_shader",
        capabilities={"overlay"},
        start_visual_contains="Matrix shader engaged",
        stop_visual_contains="Matrix shader disabled",
    ),
    EffectExpectation(
        name="uac_mirage",
        capabilities={"overlay", "ui"},
        start_visual_contains="UAC mirage displayed",
        stop_visual_contains="UAC mirage cleared",
        start_system=("modal_control", "show_uac"),
        stop_system=("modal_control", "hide_uac"),
    ),
    EffectExpectation(
        name="terminal_storm",
        capabilities={"overlay"},
        start_visual_contains="Terminal storm initiated",
        stop_visual_contains="Terminal storm silenced",
    ),
    EffectExpectation(
        name="net_outage",
        capabilities={"ui"},
        start_visual_contains="Network outage simulation triggered",
        stop_visual_contains="Network outage cleared",
        start_system=("demo_browser", "set_offline"),
        stop_system=("demo_browser", "set_online"),
    ),
    EffectExpectation(
        name="disk_full",
        capabilities={"ui"},
        start_visual_contains="Disk quota filled",
        stop_visual_contains="Disk quota cleared",
        start_system=("demo_editor", "disk_full"),
        stop_system=("demo_editor", "disk_clear"),
    ),
    EffectExpectation(
        name="cpu_heater",
        capabilities={"ui"},
        start_visual_contains="CPU heater spinning up",
        stop_visual_contains="CPU heater cooled off",
        start_system=("demo_cpu", "heat"),
        stop_system=("demo_cpu", "cool"),
    ),
    EffectExpectation(
        name="lag_spike",
        capabilities={"ui"},
        start_visual_contains="Lag spike engaged",
        stop_visual_contains="Lag spike cleared",
        start_system=("latency_sim", "start"),
        stop_system=("latency_sim", "stop"),
    ),
    EffectExpectation(
        name="typer_gremlin",
        capabilities={"ui"},
        start_visual_contains="Typer gremlin enabled",
        stop_visual_contains="Typer gremlin banished",
        start_system=("input_mutation", "duplicate"),
        stop_system=("input_mutation", "restore"),
    ),
    EffectExpectation(
        name="caps_roulette",
        capabilities={"ui"},
        start_visual_contains="Caps roulette engaged",
        stop_visual_contains="Caps roulette disabled",
        start_system=("input_mutation", "caps_shuffle"),
        stop_system=("input_mutation", "restore"),
    ),
    EffectExpectation(
        name="window_wobble",
        capabilities={"overlay", "ui"},
        start_visual_contains="Window wobble engaged",
        stop_visual_contains="Window wobble finished",
        start_system=("window_transform", "wobble_start"),
        stop_system=("window_transform", "wobble_stop"),
    ),
    EffectExpectation(
        name="ascii_snow",
        capabilities={"overlay", "audio"},
        start_visual_contains="ASCII snowflakes",
        stop_visual_contains="ASCII snow cleared",
        start_system=("overlay_animation", "start"),
        stop_system=("overlay_animation", "stop"),
    ),
    EffectExpectation(
        name="fake_update",
        capabilities={"overlay", "ui"},
        start_visual_contains="Fake update screen displayed",
        stop_visual_contains="Fake update cancelled",
    ),
    EffectExpectation(
        name="shame_bell",
        capabilities={"audio"},
        start_visual_contains="Shame bell ringing",
        stop_visual_contains="Shame bell echo fades",
        start_system=("audio_playback", None),
    ),
    EffectExpectation(
        name="ctrl_alt_b_briefing",
        capabilities={"overlay", "ui"},
        start_visual_contains="LAB-ONLY BSOD disabled",
        stop_visual_contains="BSOD briefing dismissed",
        start_system=("lab_warning", "ctrl_alt_b"),
    ),
    EffectExpectation(
        name="ctrl_alt_k_ethics",
        capabilities={"overlay", "ui"},
        start_visual_contains="LAB hook disabled",
        stop_visual_contains="Ethics reminder dismissed",
        start_system=("lab_warning", "ctrl_alt_k"),
    ),
)


@pytest.fixture()
def controller() -> tuple[EffectController, EventBus, SafetyContext]:
    bus = EventBus()
    interlocks = SafetyInterlocks(hold_to_arm_duration=0.0)
    context = SafetyContext(mode=SIM_ONLY, interlocks=interlocks)
    ctrl = EffectController(context, bus)
    return ctrl, bus, context


def test_fake_bsod_toggle(controller: tuple[EffectController, EventBus, SafetyContext]) -> None:
    ctrl, bus, context = controller
    ctrl.bind_key("F1", "fake_bsod")

    visuals: list[VisualAction] = []
    bus.subscribe(VisualAction, visuals.append)

    context.record_disruptive_confirmation("fake_bsod")
    context.record_disruptive_confirmation("fake_bsod")
    context.begin_hold_to_arm("fake_bsod")
    assert context.complete_hold_to_arm("fake_bsod")

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


def test_disruptive_effect_prompts_and_allows_after_interlocks(
    controller: tuple[EffectController, EventBus, SafetyContext]
) -> None:
    ctrl, bus, context = controller
    prompts: list[SystemAction] = []
    bus.subscribe(SystemAction, prompts.append)

    with pytest.raises(InterlockPending):
        ctrl.start_effect("fake_bsod")

    prompt_actions = [
        action
        for action in prompts
        if action.name == "safety_interlock_prompt"
        and (action.payload or {}).get("effect") == "fake_bsod"
    ]
    assert prompt_actions
    payload = prompt_actions[-1].payload or {}
    assert "double_confirm" in payload.get("pending_steps", [])
    assert payload.get("hold_to_arm_required") is True

    context.record_disruptive_confirmation("fake_bsod")
    context.record_disruptive_confirmation("fake_bsod")
    context.begin_hold_to_arm("fake_bsod")
    assert context.complete_hold_to_arm("fake_bsod")

    ctrl.start_effect("fake_bsod")
    assert "fake_bsod" in ctrl.active_effects
    ctrl.stop_effect("fake_bsod")

    with pytest.raises(InterlockPending):
        ctrl.start_effect("fake_bsod")


@pytest.mark.parametrize("case", EFFECT_CASES)
def test_new_effects_start_and_stop(
    controller: tuple[EffectController, EventBus, SafetyContext],
    case: EffectExpectation,
) -> None:
    ctrl, bus, _ = controller
    visuals: list[VisualAction] = []
    systems: list[SystemAction] = []
    bus.subscribe(VisualAction, visuals.append)
    bus.subscribe(SystemAction, systems.append)

    ctrl.start_effect(case.name)
    assert case.name in ctrl.active_effects
    assert registry.capabilities(case.name) == frozenset(case.capabilities)
    assert any(
        case.start_visual_contains in action.description for action in visuals
    )
    if case.start_system is not None:
        expected_name, expected_value = case.start_system
        assert any(
            action.name == expected_name
            and (
                expected_value is None
                or (action.payload or {}).get("action") == expected_value
                or (action.payload or {}).get("effect") == expected_value
                or (action.payload or {}).get("clip") == expected_value
                or (action.payload or {}).get("stage") == expected_value
            )
            for action in systems
        )
    effect = ctrl.get_effect(case.name)
    assert effect is not None
    assert "running" in effect.status()

    ctrl.stop_effect(case.name)
    assert case.name not in ctrl.active_effects
    assert any(
        case.stop_visual_contains in action.description for action in visuals
    )
    if case.stop_system is not None:
        expected_name, expected_value = case.stop_system
        assert any(
            action.name == expected_name
            and (
                expected_value is None
                or (action.payload or {}).get("action") == expected_value
                or (action.payload or {}).get("stage") == expected_value
            )
            for action in systems
        )
    assert "idle" in effect.status()


def test_modifier_combo_bindings(
    controller: tuple[EffectController, EventBus, SafetyContext]
) -> None:
    ctrl, bus, _ = controller
    ctrl.bind_key("CTRL+ALT+B", "ctrl_alt_b_briefing")
    visuals: list[VisualAction] = []
    bus.subscribe(VisualAction, visuals.append)

    bus.publish(
        SystemAction(
            name="key_press",
            payload={
                "key": ord("B"),
                "text": "b",
                "modifiers": 0x04000000 | 0x08000000,
            },
        )
    )

    assert "ctrl_alt_b_briefing" in ctrl.active_effects
    assert any("BSOD" in action.description for action in visuals)


def test_panic_stops_all_effects(
    controller: tuple[EffectController, EventBus, SafetyContext]
) -> None:
    ctrl, bus, context = controller
    ctrl.bind_key("F1", "fake_bsod")
    context.record_disruptive_confirmation("fake_bsod")
    context.record_disruptive_confirmation("fake_bsod")
    context.begin_hold_to_arm("fake_bsod")
    assert context.complete_hold_to_arm("fake_bsod")
    bus.publish(SystemAction(name="key_press", payload={"text": "F1"}))
    assert ctrl.active_effects

    context.panic()
    assert not ctrl.active_effects


def test_fake_locker_requires_interlock_reset(
    controller: tuple[EffectController, EventBus, SafetyContext]
) -> None:
    ctrl, _, context = controller

    with pytest.raises(InterlockPending):
        ctrl.start_effect("fake_locker")

    context.record_disruptive_confirmation("fake_locker")
    context.record_disruptive_confirmation("fake_locker")
    context.begin_hold_to_arm("fake_locker")
    assert context.complete_hold_to_arm("fake_locker")

    ctrl.start_effect("fake_locker")
    assert "fake_locker" in ctrl.active_effects
    ctrl.stop_effect("fake_locker")

    with pytest.raises(InterlockPending):
        ctrl.start_effect("fake_locker")
