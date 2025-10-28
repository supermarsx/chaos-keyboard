"""Matrix-style rain overlay effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["MatrixRainEffect"]


@dataclass
class MatrixRainEffect:
    """Render simulated green code rain in the crack console."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "matrix_rain"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"overlay", "ui"})
    _active: bool = False
    _frames_rendered: int = 0

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._frames_rendered = 0
        self.bus.publish(
            VisualAction(
                target="console",
                description="Matrix rain activated – decoding faux glyph stream.",
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            VisualAction(
                target="console",
                description="Matrix rain halted.",
            )
        )

    def status(self) -> str:
        state = "running" if self._active else "idle"
        return f"{state} ({self._frames_rendered} frames)"

    def render_frame(self) -> None:
        if not self._active:
            return
        self._frames_rendered += 1
        self.bus.publish(
            VisualAction(
                target="console",
                description=f"Matrix rain frame {self._frames_rendered}",
            )
        )


@register_effect(MatrixRainEffect.name)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return MatrixRainEffect(context=context, bus=bus)
