"""Simulation-only caps roulette text mutation effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["CapsRouletteEffect"]


@dataclass
class CapsRouletteEffect:
    """Randomise text casing inside sandboxed inputs."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "caps_roulette"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"ui"})
    _active: bool = False

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Caps roulette engaged – randomising letter casing.",
            )
        )
        self.bus.publish(
            SystemAction(
                name="input_mutation",
                payload={"action": "caps_shuffle"},
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
                description="Caps roulette disabled – original casing restored.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(CapsRouletteEffect.name, capabilities=CapsRouletteEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return CapsRouletteEffect(context=context, bus=bus)

