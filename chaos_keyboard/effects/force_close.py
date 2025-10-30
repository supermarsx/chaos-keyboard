"""Simulation-only effect closing bundled demo app windows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet, Sequence

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["ForceCloseEffect"]


@dataclass
class ForceCloseEffect:
    """Simulate force-closing the sandboxed demo applications."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "force_close"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"ui"})
    _active: bool = False
    _targets: ClassVar[Sequence[str]] = (
        "fake_editor",
        "retro_browser",
        "chat_meme_builder",
        "cpu_toy",
    )

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Force-close routine engaged for demo apps (simulation).",
            )
        )
        self.bus.publish(
            SystemAction(
                name="demo_app_control",
                payload={
                    "action": "close",
                    "targets": list(self._targets),
                    "origin": self.name,
                },
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            SystemAction(
                name="demo_app_control",
                payload={
                    "action": "restore",
                    "targets": list(self._targets),
                    "origin": self.name,
                },
            )
        )
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Demo apps reopened after simulated force close.",
            )
        )

    def status(self) -> str:
        return "running" if self._active else "idle"


@register_effect(ForceCloseEffect.name, capabilities=ForceCloseEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return ForceCloseEffect(context=context, bus=bus)

