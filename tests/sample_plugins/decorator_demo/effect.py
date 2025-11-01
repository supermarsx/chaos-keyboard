"""Sample plugin registering an effect via the decorator helper."""
from __future__ import annotations

from chaos_keyboard.bus import EventBus
from chaos_keyboard.effects import Effect
from chaos_keyboard.safety import SafetyContext


class DecoratorDemoEffect:
    """Minimal effect used for plugin loader integration tests."""

    name = "decorator_demo"
    capabilities = frozenset({"ui"})

    def __init__(self, context: SafetyContext, bus: EventBus) -> None:
        self._context = context
        self._bus = bus
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def status(self) -> str:
        return "running" if self._running else "idle"


def register(app) -> None:
    """Entry point used by :func:`load_effect_plugins`."""

    @app.register_effect(
        DecoratorDemoEffect.name, capabilities=DecoratorDemoEffect.capabilities
    )
    def _factory(context: SafetyContext, bus: EventBus) -> Effect:
        return DecoratorDemoEffect(context, bus)
