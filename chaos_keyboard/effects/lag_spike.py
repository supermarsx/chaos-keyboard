"""Simulation-only input lag spike effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["LagSpikeEffect"]


@dataclass
class LagSpikeEffect:
    """Introduce artificial latency into sandbox interactions."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "lag_spike"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"ui"})
    _active: bool = False
    _latency_ms: int = 250

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="ui",
                description=f"Lag spike engaged – adding {self._latency_ms}ms latency.",
            )
        )
        self.bus.publish(
            SystemAction(
                name="latency_sim",
                payload={"action": "start", "delay_ms": self._latency_ms},
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            SystemAction(
                name="latency_sim",
                payload={"action": "stop"},
            )
        )
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Lag spike cleared – inputs snappy again.",
            )
        )

    def status(self) -> str:
        return (
            "running"
            if self._active
            else f"idle (last lag {self._latency_ms}ms)"
        )


@register_effect(LagSpikeEffect.name, capabilities=LagSpikeEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return LagSpikeEffect(context=context, bus=bus)

