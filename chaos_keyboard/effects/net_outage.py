"""Simulation-only network outage effect for demo browser."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["NetOutageEffect"]


@dataclass
class NetOutageEffect:
    """Simulate network outage overlays within the sandbox."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "net_outage"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"ui"})
    _active: bool = False

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Network outage simulation triggered – demo apps offline.",
            )
        )
        self.bus.publish(
            SystemAction(
                name="demo_browser",
                payload={"action": "set_offline", "origin": self.name},
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            SystemAction(
                name="demo_browser",
                payload={"action": "set_online", "origin": self.name},
            )
        )
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Network outage cleared – connectivity restored.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(NetOutageEffect.name, capabilities=NetOutageEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return NetOutageEffect(context=context, bus=bus)

