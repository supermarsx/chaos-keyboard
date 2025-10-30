"""Simulation-only disk full warning effect for demo editor."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["DiskFullEffect"]


@dataclass
class DiskFullEffect:
    """Trigger faux disk-full warnings within the sandbox."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "disk_full"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"ui"})
    _active: bool = False

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Disk quota filled (simulation) – demo apps show error banners.",
            )
        )
        self.bus.publish(
            SystemAction(
                name="demo_editor",
                payload={"action": "disk_full", "quota_mb": 64},
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            SystemAction(
                name="demo_editor",
                payload={"action": "disk_clear"},
            )
        )
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Disk quota cleared – storage back to normal.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(DiskFullEffect.name, capabilities=DiskFullEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return DiskFullEffect(context=context, bus=bus)

