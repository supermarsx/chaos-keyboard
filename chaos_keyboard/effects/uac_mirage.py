"""Simulation-only UAC mirage dialog effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["UACMirageEffect"]


@dataclass
class UACMirageEffect:
    """Render a faux User Account Control prompt within the sandbox."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "uac_mirage"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"overlay", "ui"})
    _active: bool = False

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="UAC mirage displayed – training prompt only.",
            )
        )
        self.bus.publish(
            SystemAction(
                name="modal_control",
                payload={
                    "action": "show_uac",
                    "message": "Simulation: no credentials requested.",
                },
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            SystemAction(
                name="modal_control",
                payload={"action": "hide_uac"},
            )
        )
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="UAC mirage cleared.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(UACMirageEffect.name, capabilities=UACMirageEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return UACMirageEffect(context=context, bus=bus)

