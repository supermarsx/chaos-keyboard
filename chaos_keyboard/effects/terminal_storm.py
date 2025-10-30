"""Simulation-only terminal storm console spam effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["TerminalStormEffect"]


@dataclass
class TerminalStormEffect:
    """Spew faux terminal output into the Crack Console."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "terminal_storm"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"overlay"})
    _active: bool = False
    _lines_emitted: int = 0

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._lines_emitted = 0
        self.bus.publish(
            VisualAction(
                target="console",
                description="Terminal storm initiated – streaming faux nmap output.",
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            VisualAction(
                target="console",
                description="Terminal storm silenced.",
            )
        )

    def status(self) -> str:
        state = "running" if self._active else "idle"
        return f"{state} ({self._lines_emitted} lines)"

    def emit_line(self, content: str) -> None:
        """Emit an additional faux terminal log line if active."""

        if not self._active:
            return
        self._lines_emitted += 1
        self.bus.publish(
            VisualAction(
                target="console",
                description=f"Storm line: {content}",
            )
        )


@register_effect(
    TerminalStormEffect.name, capabilities=TerminalStormEffect.capabilities
)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return TerminalStormEffect(context=context, bus=bus)

