"""Unit tests for the Chaos Keyboard event bus."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chaos_keyboard.bus import EffectAction, EventBus, SystemAction, VisualAction


def test_subscribe_and_publish_invokes_callback() -> None:
    bus: EventBus = EventBus()
    received: List[EffectAction] = []

    bus.subscribe(EffectAction, received.append)

    action = EffectAction(key="A", effect="sparkle")
    bus.publish(action)

    assert received == [action]


def test_subscribers_only_receive_matching_action_type() -> None:
    bus: EventBus = EventBus()
    received_effects: List[EffectAction] = []
    received_visuals: List[VisualAction] = []

    bus.subscribe(EffectAction, received_effects.append)
    bus.subscribe(VisualAction, received_visuals.append)

    bus.publish(EffectAction(key="B", effect="flash"))

    assert len(received_effects) == 1
    assert not received_visuals


def test_unrelated_actions_do_not_trigger_subscribers() -> None:
    bus: EventBus = EventBus()
    received: List[SystemAction] = []

    bus.subscribe(SystemAction, received.append)

    bus.publish(EffectAction(key="C", effect="glow"))

    assert not received
