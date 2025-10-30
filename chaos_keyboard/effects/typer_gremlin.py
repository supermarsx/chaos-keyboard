"""Simulation-only typer gremlin duplication effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["TyperGremlinEffect"]


@dataclass
class TyperGremlinEffect:
    """Duplicate typed characters inside sandboxed inputs."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "typer_gremlin"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"ui"})
    _active: bool = False
    _probability: float = 0.3

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Typer gremlin enabled – duplicating characters mischievously.",
            )
        )
        self.bus.publish(
            SystemAction(
                name="input_mutation",
                payload={"action": "duplicate", "probability": self._probability},
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            SystemAction(
                name="input_mutation",
                payload={"action": "restore"},
            )
        )
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Typer gremlin banished – inputs stabilized.",
            )
        )

    def status(self) -> str:
        state = "running" if self._active else "idle"
        return f"{state} (p={self._probability:.1f})"


@register_effect(TyperGremlinEffect.name, capabilities=TyperGremlinEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return TyperGremlinEffect(context=context, bus=bus)

