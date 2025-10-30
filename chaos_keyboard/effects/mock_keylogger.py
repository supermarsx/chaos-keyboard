"""Mock keylogger effect recording keystrokes typed into the app."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, ClassVar, FrozenSet, List

from ..bus import EventBus, SystemAction, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["MockKeyloggerEffect"]


@dataclass
class MockKeyloggerEffect:
    """Capture keystrokes published on the event bus."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "mock_keylogger"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"ui"})
    _active: bool = False
    _buffer: List[str] = field(default_factory=list)
    _unsubscribe: Callable[[], None] | None = None

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._unsubscribe = self.bus.subscribe(SystemAction, self._on_system_action)
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Mock keylogger activated – capturing in-app keystrokes.",
            )
        )

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        self.bus.publish(
            VisualAction(
                target="ui",
                description="Mock keylogger deactivated.",
            )
        )

    def status(self) -> str:
        captured = "".join(self._buffer) or "<empty>"
        return "running" if self._active else f"idle (captured {captured})"

    def _on_system_action(self, action: SystemAction) -> None:
        if not self._active or action.name != "key_press":
            return
        payload = action.payload or {}
        text = payload.get("text")
        if not text:
            return
        self._buffer.append(str(text))
        self.bus.publish(
            VisualAction(
                target="ui",
                description=f"Mock keylogger captured: {text}",
            )
        )


@register_effect(
    MockKeyloggerEffect.name, capabilities=MockKeyloggerEffect.capabilities
)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return MockKeyloggerEffect(context=context, bus=bus)
