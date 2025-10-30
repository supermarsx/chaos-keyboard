"""Simulation-only Ctrl+Alt+B BSOD briefing effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["CtrlAltBBriefingEffect"]


@dataclass
class CtrlAltBBriefingEffect:
    """Explain why the lab-only BSOD is disabled in public builds."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "ctrl_alt_b_briefing"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"overlay", "ui"})
    _active: bool = False

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="LAB-ONLY BSOD disabled – showing safety briefing instead.",
            )
        )
        self.bus.publish(
            SystemAction(
                name="lab_warning",
                payload={
                    "effect": "ctrl_alt_b",
                    "message": "Rebuild with LAB_ENABLE to trigger real BSOD in disposable labs only.",
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
                description="BSOD briefing dismissed.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(
    CtrlAltBBriefingEffect.name, capabilities=CtrlAltBBriefingEffect.capabilities
)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return CtrlAltBBriefingEffect(context=context, bus=bus)

