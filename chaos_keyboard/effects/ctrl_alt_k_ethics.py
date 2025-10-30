"""Simulation-only Ctrl+Alt+K ethics dialog effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["CtrlAltKEthicsEffect"]


@dataclass
class CtrlAltKEthicsEffect:
    """Show an ethics reminder when the lab-only hook combo is pressed."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "ctrl_alt_k_ethics"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"overlay", "ui"})
    _active: bool = False

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="LAB hook disabled – presenting ethics reminder.",
            )
        )
        self.bus.publish(
            SystemAction(
                name="lab_warning",
                payload={
                    "effect": "ctrl_alt_k",
                    "message": "Input hooks ship only in lab builds with legal approvals.",
                },
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="Ethics reminder dismissed.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(
    CtrlAltKEthicsEffect.name, capabilities=CtrlAltKEthicsEffect.capabilities
)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return CtrlAltKEthicsEffect(context=context, bus=bus)

