"""Simulation-only high contrast UI toggle effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["HighContrastEffect"]


@dataclass
class HighContrastEffect:
    """Apply a simulated high contrast palette inside the UI."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "high_contrast"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"ui"})
    _active: bool = False

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="ui",
                description="High contrast theme activated (simulation).",
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            VisualAction(
                target="ui",
                description="High contrast theme restored to default palette.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(HighContrastEffect.name, capabilities=HighContrastEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return HighContrastEffect(context=context, bus=bus)

