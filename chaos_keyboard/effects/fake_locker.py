"""Simulation-only fake locker overlay effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["FakeLockerEffect"]


@dataclass
class FakeLockerEffect:
    """Display a simulated ransomware-style lock screen."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "fake_locker"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"overlay", "ui"})
    _active: bool = False

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="Fake locker engaged – solve the puzzle to "
                "dismiss (simulation).",
            )
        )
        self.bus.publish(
            SystemAction(
                name="modal_control",
                payload={"action": "show_lock_screen", "origin": self.name},
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            SystemAction(
                name="modal_control",
                payload={"action": "hide_lock_screen", "origin": self.name},
            )
        )
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="Fake locker dismissed – freedom restored.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(FakeLockerEffect.name, capabilities=FakeLockerEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return FakeLockerEffect(context=context, bus=bus)

