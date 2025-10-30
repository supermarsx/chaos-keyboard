"""Simulation-only CPU heater workload effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["CpuHeaterEffect"]


@dataclass
class CpuHeaterEffect:
    """Peg a faux worker thread for dramatic effect."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "cpu_heater"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"ui"})
    _active: bool = False
    _cycles: int = 0

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._cycles = 0
        self.bus.publish(
            VisualAction(
                target="ui",
                description="CPU heater spinning up synthetic load (simulation).",
            )
        )
        self.bus.publish(
            SystemAction(
                name="demo_cpu",
                payload={"action": "heat", "load": 0.85},
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            SystemAction(
                name="demo_cpu",
                payload={"action": "cool", "cycles": self._cycles},
            )
        )
        self.bus.publish(
            VisualAction(
                target="ui",
                description="CPU heater cooled off.",
            )
        )

    def status(self) -> str:
        state = "running" if self._active else "idle"
        return f"{state} ({self._cycles} cycles)"

    def simulate_cycle(self) -> None:
        """Increment the simulated workload cycle count if active."""

        if not self._active:
            return
        self._cycles += 1
        self.bus.publish(
            VisualAction(
                target="ui",
                description=f"CPU heater cycle {self._cycles}",
            )
        )


@register_effect(CpuHeaterEffect.name, capabilities=CpuHeaterEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return CpuHeaterEffect(context=context, bus=bus)

