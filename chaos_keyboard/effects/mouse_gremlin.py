"""Simulation-only mouse gremlin cursor mischief effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["MouseGremlinEffect"]


@dataclass
class MouseGremlinEffect:
    """Cause the sandboxed cursor to wander mischievously."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "mouse_gremlin"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"ui"})
    _active: bool = False
    _wiggles: int = 0

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._wiggles = 0
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Mouse gremlin released – cursor jiggle simulation running.",
            )
        )
        self.bus.publish(
            SystemAction(
                name="pointer_gremlin",
                payload={"action": "start", "pattern": "jiggle"},
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            SystemAction(
                name="pointer_gremlin",
                payload={"action": "stop", "wiggles": self._wiggles},
            )
        )
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Mouse gremlin contained – pointer calm again.",
            )
        )

    def status(self) -> str:
        state = "running" if self._active else "idle"
        return f"{state} ({self._wiggles} wiggles)"

    def register_wiggle(self) -> None:
        """Increment the recorded wiggle count for telemetry/tests."""

        if not self._active:
            return
        self._wiggles += 1
        self.bus.publish(
            VisualAction(
                target="ui",
                description=f"Mouse gremlin wiggle count: {self._wiggles}",
            )
        )


@register_effect(MouseGremlinEffect.name, capabilities=MouseGremlinEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return MouseGremlinEffect(context=context, bus=bus)

