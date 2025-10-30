"""Simulation-only fake update progress overlay effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["FakeUpdateEffect"]


@dataclass
class FakeUpdateEffect:
    """Display a faux OS update progress animation."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "fake_update"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"overlay", "ui"})
    _active: bool = False
    _progress: int = 0

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._progress = 0
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="Fake update screen displayed – please enjoy the loading bar.",
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="Fake update cancelled – returning to desktop.",
            )
        )

    def status(self) -> str:
        state = "running" if self._active else "idle"
        return f"{state} ({self._progress}% complete)"

    def advance(self, amount: int = 10) -> None:
        """Advance the faux update progress."""

        if not self._active:
            return
        self._progress = max(0, min(100, self._progress + amount))
        self.bus.publish(
            VisualAction(
                target="overlay",
                description=f"Fake update progress: {self._progress}%",
            )
        )


@register_effect(FakeUpdateEffect.name, capabilities=FakeUpdateEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return FakeUpdateEffect(context=context, bus=bus)

