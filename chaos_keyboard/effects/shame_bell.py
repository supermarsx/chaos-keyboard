"""Simulation-only shame bell audio gag effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["ShameBellEffect"]


@dataclass
class ShameBellEffect:
    """Ring a dramatic shame bell through the simulated audio pipeline."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "shame_bell"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"audio"})
    _active: bool = False
    _rings: int = 0

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._rings += 1
        self.bus.publish(
            VisualAction(
                target="audio",
                description="Shame bell ringing (simulation).",
            )
        )
        self.bus.publish(
            SystemAction(
                name="audio_playback",
                payload={"clip": "shame_bell", "loops": 1},
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            VisualAction(
                target="audio",
                description="Shame bell echo fades.",
            )
        )

    def status(self) -> str:
        state = "running" if self._active else "idle"
        return f"{state} ({self._rings} rings)"


@register_effect(ShameBellEffect.name, capabilities=ShameBellEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return ShameBellEffect(context=context, bus=bus)

