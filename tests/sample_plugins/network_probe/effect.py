"""Sample plugin requesting LAB-only network capability."""
from __future__ import annotations

from chaos_keyboard.bus import EventBus
from chaos_keyboard.safety import SafetyContext


class NetworkProbeEffect:
    """Effect that should be blocked in SIM ONLY mode."""

    name = "network_probe"
    capabilities = frozenset({"network"})

    def __init__(self, context: SafetyContext, bus: EventBus) -> None:
        self._context = context
        self._bus = bus

    def start(self) -> None:
        # Real implementation would initiate a network call; we keep it inert.
        return None

    def stop(self) -> None:
        return None

    def status(self) -> str:
        return "idle"


def register(app) -> None:
    """Register the effect using the direct factory helper."""

    def _factory(context: SafetyContext, bus: EventBus) -> NetworkProbeEffect:
        return NetworkProbeEffect(context, bus)

    app.register_factory(
        NetworkProbeEffect.name,
        _factory,
        capabilities=NetworkProbeEffect.capabilities,
    )
