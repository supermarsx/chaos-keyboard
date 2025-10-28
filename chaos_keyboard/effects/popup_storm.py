"""Simulated popup storm effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["PopupStormEffect"]


@dataclass
class PopupStormEffect:
    """Emit a burst of faux popups inside the application."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "popup_storm"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"ui"})
    _active: bool = False
    _count: int = 0

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._count += 1
        self.bus.publish(
            VisualAction(
                target="ui",
                description=(
                    "Popup storm #{:02d} unleashed – spawning retro dialog spam.".format(
                        self._count
                    )
                ),
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Popup storm cleared.",
            )
        )

    def status(self) -> str:
        return f"running (burst {self._count})" if self._active else "idle"


@register_effect(PopupStormEffect.name)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return PopupStormEffect(context=context, bus=bus)
