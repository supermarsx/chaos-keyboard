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


def test_status_indicator_tracks_effects_and_fps() -> None:
    indicators = StatusIndicators()
    assert indicators.effects_chip() == "Effects: NONE"
    assert indicators.fps_chip() == "FPS: --"

    assert indicators.handle_system_action(
        SystemAction(name="effect_started", payload={"effect": "matrix_shader"})
    )
    assert indicators.effects_chip() == "Effects: ▣ MATRIX_SHADER"

    assert not indicators.handle_system_action(
        SystemAction(name="effect_started", payload={"effect": "matrix_shader"})
    )

    indicators.handle_system_action(
        SystemAction(name="effect_started", payload={"effect": "fake_bsod"})
    )
    assert indicators.effects_chip() == "Effects: ▣ FAKE_BSOD ▣ MATRIX_SHADER"

    assert indicators.handle_system_action(
        SystemAction(name="frame_timing", payload={"fps": 59.94})
    )
    assert indicators.fps_chip() == "FPS: 59.9"

    assert not indicators.handle_system_action(
        SystemAction(name="frame_timing", payload={"fps": 59.94})
    )

    assert indicators.handle_system_action(
        SystemAction(name="effect_stopped", payload={"effect": "matrix_shader"})
    )
    assert indicators.effects_chip() == "Effects: ▣ FAKE_BSOD"

    assert indicators.handle_system_action(
        SystemAction(name="effect_stopped", payload={"effect": "fake_bsod"})
    )
    assert indicators.effects_chip() == "Effects: NONE"
