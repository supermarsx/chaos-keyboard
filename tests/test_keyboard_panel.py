"""Tests for the Qt keyboard panel widget."""
from __future__ import annotations

from typing import List

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from chaos_keyboard.bus import EffectAction, EventBus, SystemAction
from chaos_keyboard.ui import KeyboardPanel


@pytest.fixture()
def qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(["pytest-chaos-keyboard"])
    yield app


def test_layout_toggle_publishes_system_action(qt_app: QApplication) -> None:
    bus = EventBus()
    actions: List[SystemAction] = []
    bus.subscribe(SystemAction, actions.append)

    panel = KeyboardPanel(bus, effect_bindings=())
    assert actions
    layout_events = [action for action in actions if action.name == "keyboard_layout"]
    assert layout_events
    assert layout_events[-1].payload == {"layout": "ANSI"}

    actions.clear()
    panel.set_active_layout("ISO")
    assert actions
    iso_events = [action for action in actions if action.name == "keyboard_layout"]
    assert iso_events
    assert iso_events[-1].payload == {"layout": "ISO"}


def test_virtual_key_press_emits_effect_action(qt_app: QApplication) -> None:
    bus = EventBus()
    system_actions: List[SystemAction] = []
    effect_actions: List[EffectAction] = []
    bus.subscribe(SystemAction, system_actions.append)
    bus.subscribe(EffectAction, effect_actions.append)

    panel = KeyboardPanel(bus, effect_bindings=((Qt.Key_F1, "fake_bsod"),))
    system_actions.clear()
    effect_actions.clear()

    panel.press_key("F1")

    key_events = [action for action in system_actions if action.name == "key_press"]
    assert key_events
    payload = key_events[-1].payload or {}
    assert payload.get("key") == Qt.Key_F1

    assert effect_actions
    assert effect_actions[-1].effect == "fake_bsod"
    assert effect_actions[-1].key == "F1"
