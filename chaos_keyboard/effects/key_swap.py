"""Simulation-only keyboard swap effect for bundled inputs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Dict, FrozenSet

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["KeySwapEffect"]


@dataclass
class KeySwapEffect:
    """Swap key output within sandboxed text fields."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "key_swap"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"ui"})
    _active: bool = False
    _mapping: Dict[str, str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._mapping = {"A": "S", "S": "A", "Q": "W", "W": "Q"}

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Key swap chaos enabled – keys trading places inside the sandbox.",
            )
        )
        self.bus.publish(
            SystemAction(
                name="input_mutation",
                payload={"action": "swap", "mapping": dict(self._mapping)},
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            SystemAction(
                name="input_mutation",
                payload={"action": "restore"},
            )
        )
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Key swap disabled – inputs restored.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(KeySwapEffect.name, capabilities=KeySwapEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return KeySwapEffect(context=context, bus=bus)

