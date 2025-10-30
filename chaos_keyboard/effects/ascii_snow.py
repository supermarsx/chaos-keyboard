"""Simulation-only ASCII snow overlay effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["AsciiSnowEffect"]


@dataclass
class AsciiSnowEffect:
    """Render festive ASCII snowfall over the UI."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "ascii_snow"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"overlay", "audio"})
    _active: bool = False

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="ASCII snowflakes drifting across the display.",
            )
        )
        self.bus.publish(
            SystemAction(
                name="overlay_animation",
                payload={"action": "start", "effect": "ascii_snow"},
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            SystemAction(
                name="overlay_animation",
                payload={"action": "stop", "effect": "ascii_snow"},
            )
        )
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="ASCII snow cleared – back to the matrix.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(AsciiSnowEffect.name, capabilities=AsciiSnowEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return AsciiSnowEffect(context=context, bus=bus)

