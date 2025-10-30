"""Simulation-only fake data exfiltration progress effect."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, FrozenSet, List

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["FakeExfilEffect"]


@dataclass
class FakeExfilEffect:
    """Animate a faux exfiltration progress sequence."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "fake_exfil"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"ui"})
    _active: bool = False
    _progress: int = 0
    _manifest: List[str] = field(
        default_factory=lambda: [
            "payroll_q1.csv",
            "vault-config.json",
            "server_room_badge_ids.txt",
        ]
    )

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._progress = 0
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Fake exfiltration initiated – staging files to blackhole://dev/null.",
            )
        )
        self.bus.publish(
            SystemAction(
                name="fake_exfiltration",
                payload={"stage": "begin", "manifest": list(self._manifest)},
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            SystemAction(
                name="fake_exfiltration",
                payload={"stage": "complete", "progress": self._progress},
            )
        )
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Fake exfiltration cancelled; files never left the sandbox.",
            )
        )

    def status(self) -> str:
        state = "running" if self._active else "idle"
        return f"{state} ({self._progress}% complete)"

    def advance(self, amount: int = 15) -> None:
        """Advance the simulated transfer progress."""

        if not self._active:
            return
        self._progress = max(0, min(100, self._progress + amount))
        self.bus.publish(
            VisualAction(
                target="ui",
                description=f"Fake exfiltration progress: {self._progress}%",
            )
        )


@register_effect(FakeExfilEffect.name, capabilities=FakeExfilEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return FakeExfilEffect(context=context, bus=bus)

