"""Simulation-only window wobble overlay effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["WindowWobbleEffect"]


@dataclass
class WindowWobbleEffect:
    """Shake the UI like an old CRT being degaussed."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "window_wobble"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"overlay", "ui"})
    _active: bool = False

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="Window wobble engaged – CRT degauss animation running.",
            )
        )
        self.bus.publish(
            SystemAction(
                name="window_transform",
                payload={"action": "wobble_start"},
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            SystemAction(
                name="window_transform",
                payload={"action": "wobble_stop"},
            )
        )
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="Window wobble finished – screen steady.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(WindowWobbleEffect.name, capabilities=WindowWobbleEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return WindowWobbleEffect(context=context, bus=bus)

