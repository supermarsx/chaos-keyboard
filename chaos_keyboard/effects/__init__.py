"""Effect system and registry for Chaos Keyboard."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, FrozenSet, Protocol, Sequence

from ..bus import EffectAction, EventBus, SystemAction
from ..safety import CapabilityNotAllowed, SafetyContext

__all__ = [
    "Effect",
    "EffectFactory",
    "EffectRegistry",
    "EffectController",
    "register_effect",
    "registry",
]


class Effect(Protocol):
    """Protocol describing the lifecycle of an effect."""

    name: str
    capabilities: FrozenSet[str]

    def start(self) -> None:
        """Start the effect."""

    def stop(self) -> None:
        """Stop the effect."""

    def status(self) -> str:
        """Return a human readable status for the effect."""


EffectFactory = Callable[[SafetyContext, EventBus], Effect]


@dataclass
class EffectRegistry:
    """Registry of available effect factories."""

    _factories: Dict[str, EffectFactory]

    def register(self, name: str, factory: EffectFactory) -> None:
        """Register a factory for the given effect name."""

        key = name.strip().lower()
        if key in self._factories:
            raise ValueError(f"Effect '{name}' is already registered")
        self._factories[key] = factory

    def unregister(self, name: str) -> None:
        """Remove a previously registered effect factory."""

        self._factories.pop(name.strip().lower(), None)

    def load(self, name: str, context: SafetyContext, bus: EventBus) -> Effect:
        """Instantiate the named effect."""

        key = name.strip().lower()
        try:
            factory = self._factories[key]
        except KeyError as exc:
            raise KeyError(f"Unknown effect '{name}'") from exc
        return factory(context, bus)

    def names(self) -> Sequence[str]:
        """Return a sorted sequence of registered effect names."""

        return tuple(sorted(self._factories))


registry = EffectRegistry(_factories={})


def register_effect(name: str) -> Callable[[EffectFactory], EffectFactory]:
    """Decorator registering an effect factory under ``name``."""

    def decorator(factory: EffectFactory) -> EffectFactory:
        registry.register(name, factory)
        return factory

    return decorator


class EffectController:
    """Coordinate effect lifecycle in response to bus actions."""

    def __init__(self, context: SafetyContext, bus: EventBus) -> None:
        self._context = context
        self._bus = bus
        self._key_bindings: Dict[str, str] = {}
        self._instances: Dict[str, Effect] = {}
        self._active: set[str] = set()
        self._system_unsubscribe: Callable[[], None] | None = bus.subscribe(
            SystemAction, self._on_system_action
        )
        self._watchdog_unsubscribe: Callable[[], None] | None = (
            context.watchdog.register(self.stop_all)
        )

    @property
    def active_effects(self) -> frozenset[str]:
        """Return a snapshot of currently running effects."""

        return frozenset(self._active)

    def bind_key(self, key: object, effect_name: str) -> None:
        """Bind a keyboard identifier to an effect name."""

        self._key_bindings[self._normalise_key(key)] = effect_name.strip().lower()

    def unbind_key(self, key: object) -> None:
        """Remove a previously bound key."""

        self._key_bindings.pop(self._normalise_key(key), None)

    def get_effect(self, name: str) -> Effect | None:
        """Return an instantiated effect if available."""

        return self._instances.get(name.strip().lower())

    def start_effect(self, name: str, *, source: str | None = None) -> None:
        """Start an effect by name, enforcing safety capabilities."""

        key = name.strip().lower()
        if key in self._active:
            return
        effect = self._instances.get(key)
        if effect is None:
            effect = registry.load(key, self._context, self._bus)
            self._instances[key] = effect
        try:
            self._context.require_capabilities(effect.capabilities)
        except CapabilityNotAllowed:
            if self._instances.get(key) is effect:
                self._instances.pop(key, None)
            raise
        effect.start()
        self._active.add(key)
        origin = source if source is not None else ""
        self._bus.publish(EffectAction(key=origin, effect=key))
        self._bus.publish(SystemAction(name="effect_started", payload={"effect": key}))

    def stop_effect(self, name: str) -> None:
        """Stop a running effect if active."""

        key = name.strip().lower()
        if key not in self._active:
            return
        effect = self._instances.get(key)
        if effect is None:
            self._active.discard(key)
            return
        effect.stop()
        self._active.discard(key)
        self._bus.publish(SystemAction(name="effect_stopped", payload={"effect": key}))

    def toggle_effect(self, name: str, *, source: str | None = None) -> None:
        """Toggle an effect on or off."""

        if name.strip().lower() in self._active:
            self.stop_effect(name)
        else:
            self.start_effect(name, source=source)

    def stop_all(self) -> None:
        """Stop all running effects."""

        for effect_name in list(self._active):
            self.stop_effect(effect_name)

    def close(self) -> None:
        """Release subscriptions and stop all effects."""

        self.stop_all()
        if self._system_unsubscribe is not None:
            self._system_unsubscribe()
            self._system_unsubscribe = None
        if self._watchdog_unsubscribe is not None:
            self._watchdog_unsubscribe()
            self._watchdog_unsubscribe = None

    def _on_system_action(self, action: SystemAction) -> None:
        if action.name != "key_press":
            return
        payload = action.payload or {}
        for candidate in (payload.get("key"), payload.get("text")):
            if candidate is None:
                continue
            normalised = self._normalise_key(candidate)
            effect_name = self._key_bindings.get(normalised)
            if effect_name is None:
                continue
            try:
                self.toggle_effect(effect_name, source=normalised)
            except CapabilityNotAllowed:
                # Propagate but ensure we do not leave the effect flagged active
                self._active.discard(effect_name)
                raise
            break

    @staticmethod
    def _normalise_key(key: object) -> str:
        if isinstance(key, str):
            return key.strip().upper()
        return str(key)


# Import built-in effects so they register with the global registry.
from . import fake_bsod as _fake_bsod  # noqa: E402,F401
from . import matrix_rain as _matrix_rain  # noqa: E402,F401
from . import mock_keylogger as _mock_keylogger  # noqa: E402,F401
from . import popup_storm as _popup_storm  # noqa: E402,F401
