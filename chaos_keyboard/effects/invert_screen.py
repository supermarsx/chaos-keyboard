"""Simulation-only screen inversion overlay effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["InvertScreenEffect"]


@dataclass
class InvertScreenEffect:
    """Toggle an inverted color shader across the simulated UI."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "invert_screen"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"overlay"})
    _active: bool = False

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="Invert screen shader enabled (simulation).",
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="Invert screen shader disabled.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(
    InvertScreenEffect.name, capabilities=InvertScreenEffect.capabilities
)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return InvertScreenEffect(context=context, bus=bus)

