"""Tests covering console and status bar state helpers."""
from __future__ import annotations

from chaos_keyboard.bus import SystemAction, VisualAction
from chaos_keyboard.console import ConsoleBuffer
from chaos_keyboard.status import StatusIndicators


def test_console_buffer_type_out_and_scroll() -> None:
    buffer = ConsoleBuffer(capacity=2, chars_per_tick=4)

    buffer.handle_visual_action(
        VisualAction(target="ui", description="Alpha mission engaged")
    )
    assert buffer.render_lines() == ()

    buffer.step()
    first_lines = buffer.render_lines()
    assert first_lines
    assert len(first_lines[0]) == 4

    buffer.step()
    second_lines = buffer.render_lines()
    assert second_lines
    assert second_lines[0].startswith("0x0001 ▸")

    buffer.step()
    third_lines = buffer.render_lines()
    assert third_lines
    assert third_lines[0].startswith("0x0001 ▸ UI:")

    buffer.step(ticks=10)
    complete_lines = buffer.render_lines()
    assert len(complete_lines) == 1
    assert complete_lines[0].endswith("ALPHA MISSION ENGAGED")

    buffer.handle_visual_action(
        VisualAction(target="overlay", description="Second wave incoming")
    )
    buffer.flush()
    filled_lines = buffer.render_lines()
    assert len(filled_lines) == 2
    assert filled_lines[0].endswith("ALPHA MISSION ENGAGED")
    assert filled_lines[1].endswith("SECOND WAVE INCOMING")

    buffer.handle_visual_action(
        VisualAction(target="console", description="Third message")
    )
    buffer.flush()
    overflow_lines = buffer.render_lines()
    assert len(overflow_lines) == 2
    assert overflow_lines[0].endswith("SECOND WAVE INCOMING")
    assert overflow_lines[1].endswith("THIRD MESSAGE")


def test_status_indicator_chip_metadata_updates() -> None:
    indicators = StatusIndicators()

    mode_chip = indicators.mode_chip()
    assert mode_chip.label == "Mode"
    assert mode_chip.value == "SIM ONLY"
    assert mode_chip.state == "mode-sim"
    assert "Simulation-only" in (mode_chip.tooltip or "")

    effects_chip = indicators.effects_chip()
    assert effects_chip.label == "Effects"
    assert effects_chip.value == "NONE"
    assert effects_chip.state == "effects-idle"

    fps_chip = indicators.fps_chip()
    assert fps_chip.label == "FPS"
    assert fps_chip.value == "--"
    assert fps_chip.state == "fps-idle"

    assert indicators.handle_system_action(
        SystemAction(name="runtime_mode", payload={"mode": "LAB"})
    )
    lab_chip = indicators.mode_chip()
    assert lab_chip.value == "LAB"
    assert lab_chip.state == "mode-lab"

    assert indicators.handle_system_action(
        SystemAction(name="effect_started", payload={"effect": "matrix_shader"})
    )
    first_effect_chip = indicators.effects_chip()
    assert first_effect_chip.value == "▣ MATRIX_SHADER"
    assert first_effect_chip.state == "effects-active"

    assert not indicators.handle_system_action(
        SystemAction(name="effect_started", payload={"effect": "matrix_shader"})
    )

    indicators.handle_system_action(
        SystemAction(name="effect_started", payload={"effect": "fake_bsod"})
    )
    combined_effect_chip = indicators.effects_chip()
    assert combined_effect_chip.value == "▣ FAKE_BSOD ▣ MATRIX_SHADER"
    assert combined_effect_chip.state == "effects-active"

    assert indicators.handle_system_action(
        SystemAction(name="frame_timing", payload={"fps": 59.94})
    )
    fps_active_chip = indicators.fps_chip()
    assert fps_active_chip.value == "59.9"
    assert fps_active_chip.state == "fps-active"

    assert not indicators.handle_system_action(
        SystemAction(name="frame_timing", payload={"fps": 59.94})
    )

    assert indicators.handle_system_action(
        SystemAction(name="panic_invoked", payload={"source": "test"})
    )
    reset_effects_chip = indicators.effects_chip()
    assert reset_effects_chip.value == "NONE"
    assert reset_effects_chip.state == "effects-idle"
    reset_fps_chip = indicators.fps_chip()
    assert reset_fps_chip.value == "--"
    assert reset_fps_chip.state == "fps-idle"

    assert indicators.handle_system_action(
        SystemAction(name="effect_started", payload={"effect": "fake_bsod"})
    )
    assert indicators.effects_chip().value == "▣ FAKE_BSOD"

    assert indicators.handle_system_action(
        SystemAction(name="effect_stopped", payload={"effect": "fake_bsod"})
    )
    assert indicators.effects_chip().value == "NONE"
