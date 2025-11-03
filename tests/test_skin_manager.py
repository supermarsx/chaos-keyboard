"""Tests covering the UI skin manager integration with the main window."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from chaos_keyboard.app import MainWindow
from chaos_keyboard.bus import EventBus, VisualAction
from chaos_keyboard.config import (
    AudioSettings,
    EffectSettings,
    LimitSettings,
    ProfileConfig,
    SafetySettings,
    UISettings,
)
from chaos_keyboard.safety import RuntimeMode


@pytest.fixture()
def qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(["pytest-chaos-keyboard"])
    yield app


def _profile(skin: str, scanlines: bool) -> ProfileConfig:
    return ProfileConfig(
        name="test",
        ui=UISettings(skin=skin, scanlines=scanlines, fullscreen=False),
        audio=AudioSettings(enabled=False, music=False, sfx=False),
        safety=SafetySettings(mode=RuntimeMode.SIM_ONLY),
        effects=EffectSettings(enabled=()),
        limits=LimitSettings(max_popups=8, cpu_ms=120),
    )


def test_skin_application_sets_properties_and_events(qt_app: QApplication) -> None:
    bus = EventBus()
    visual_events: list[VisualAction] = []
    bus.subscribe(VisualAction, visual_events.append)

    window = MainWindow(profile=_profile("dmg_boy", scanlines=False), event_bus=bus)
    try:
        assert window.property("skin") == "dmg_boy"
        assert window.property("scanlines") is False
        shader_payload = window.property("skinShader")
        assert isinstance(shader_payload, dict)
        assert shader_payload.get("name") == "dmg_boy"
        fragment = shader_payload.get("fragment", "")
        assert "DMG handheld" in fragment
        assert any(action.target == "ui_skin" for action in visual_events)
        assert any(action.target == "ui_shader" for action in visual_events)
    finally:
        window.close()


def test_skin_switch_updates_stylesheet_and_palette(qt_app: QApplication) -> None:
    window = MainWindow(profile=_profile("crt", scanlines=False))
    try:
        window._skin = "trs_vibe"
        window._scanlines_enabled = True
        window._apply_profile_configuration()

        assert window.property("skin") == "trs_vibe"
        assert window.property("scanlines") is True
        stylesheet = window.styleSheet()
        assert "repeating-linear-gradient" in stylesheet
        palette = window.palette()
        assert palette.color(QPalette.Window).name().lower() == "#160c04"
    finally:
        window.close()
