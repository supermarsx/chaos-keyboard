"""Simulation-only fake BSOD overlay effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["FakeBSODEffect"]


@dataclass
class FakeBSODEffect:
    """Display a faux BSOD overlay within the application."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "fake_bsod"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"overlay", "ui"})
    _active: bool = False

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="Fake BSOD overlay engaged (simulation only).",
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="Fake BSOD overlay dismissed.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(
    FakeBSODEffect.name, capabilities=FakeBSODEffect.capabilities
)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return FakeBSODEffect(context=context, bus=bus)
