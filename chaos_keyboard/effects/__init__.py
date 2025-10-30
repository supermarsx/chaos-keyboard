"""Effect system and registry for Chaos Keyboard."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, ClassVar, Dict, FrozenSet, Iterable, Mapping, Protocol, Sequence

from ..bus import EffectAction, EventBus, SystemAction
from ..logging import TelemetryLogger
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
    _capabilities: Dict[str, FrozenSet[str]]

    def register(
        self,
        name: str,
        factory: EffectFactory,
        *,
        capabilities: Iterable[str] | None = None,
    ) -> None:
        """Register a factory for the given effect name."""

        key = name.strip().lower()
        if key in self._factories:
            raise ValueError(f"Effect '{name}' is already registered")
        self._factories[key] = factory
        self._capabilities[key] = self._normalise_capabilities(capabilities)

    def unregister(self, name: str) -> None:
        """Remove a previously registered effect factory."""

        key = name.strip().lower()
        self._factories.pop(key, None)
        self._capabilities.pop(key, None)

    def load(self, name: str, context: SafetyContext, bus: EventBus) -> Effect:
        """Instantiate the named effect."""

        key = name.strip().lower()
        try:
            factory = self._factories[key]
        except KeyError as exc:
            raise KeyError(f"Unknown effect '{name}'") from exc
        return factory(context, bus)

    def capabilities(self, name: str) -> FrozenSet[str]:
        """Return the declared capabilities for ``name``."""

        key = name.strip().lower()
        try:
            return self._capabilities[key]
        except KeyError as exc:
            raise KeyError(f"Unknown effect '{name}'") from exc

    @staticmethod
    def _normalise_capabilities(
        capabilities: Iterable[str] | None,
    ) -> FrozenSet[str]:
        if capabilities is None:
            return frozenset()
        if isinstance(capabilities, str):
            raise TypeError(
                "Capabilities must be an iterable of strings, not a single string."
            )
        return frozenset(str(capability).strip().lower() for capability in capabilities)

    def names(self) -> Sequence[str]:
        """Return a sorted sequence of registered effect names."""

        return tuple(sorted(self._factories))


registry = EffectRegistry(_factories={}, _capabilities={})


def register_effect(
    name: str, *, capabilities: Iterable[str] | None = None
) -> Callable[[EffectFactory], EffectFactory]:
    """Decorator registering an effect factory under ``name``."""

    def decorator(factory: EffectFactory) -> EffectFactory:
        registry.register(name, factory, capabilities=capabilities)
        return factory

    return decorator


class EffectController:
    """Coordinate effect lifecycle in response to bus actions."""

    def __init__(
        self,
        context: SafetyContext,
        bus: EventBus,
        *,
        telemetry: TelemetryLogger | None = None,
    ) -> None:
        self._context = context
        self._bus = bus
        self._key_bindings: Dict[str, str] = {}
        self._instances: Dict[str, Effect] = {}
        self._active: set[str] = set()
        self._telemetry = telemetry
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
        required_capabilities = (
            registry.capabilities(key) if effect is None else effect.capabilities
        )
        self._context.require_capabilities(required_capabilities)
        if effect is None:
            effect = registry.load(key, self._context, self._bus)
            self._instances[key] = effect
        effect.start()
        self._active.add(key)
        origin = source if source is not None else ""
        self._bus.publish(EffectAction(key=origin, effect=key))
        self._bus.publish(SystemAction(name="effect_started", payload={"effect": key}))
        if self._telemetry is not None:
            payload = {"effect": key}
            if origin:
                payload["source"] = origin
            self._telemetry.log("effect_started", payload=payload)

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
        if self._telemetry is not None:
            self._telemetry.log("effect_stopped", payload={"effect": key})

    def toggle_effect(self, name: str, *, source: str | None = None) -> None:
        """Toggle an effect on or off."""

        if name.strip().lower() in self._active:
            self.stop_effect(name)
        else:
            self.start_effect(name, source=source)

    def stop_all(self) -> None:
        """Stop all running effects."""

        stopped = list(self._active)
        for effect_name in stopped:
            self.stop_effect(effect_name)
        if self._telemetry is not None:
            self._telemetry.log("all_effects_stopped", payload={"count": len(stopped)})

    def close(self) -> None:
        """Release subscriptions and stop all effects."""

        self.stop_all()
        if self._system_unsubscribe is not None:
            self._system_unsubscribe()
            self._system_unsubscribe = None
        if self._watchdog_unsubscribe is not None:
            self._watchdog_unsubscribe()
            self._watchdog_unsubscribe = None

    _MODIFIER_FLAGS: ClassVar[tuple[tuple[int, str], ...]] = (
        (0x02000000, "SHIFT"),
        (0x04000000, "CTRL"),
        (0x08000000, "ALT"),
        (0x10000000, "META"),
    )

    def _on_system_action(self, action: SystemAction) -> None:
        if action.name != "key_press":
            return
        payload: Mapping[str, object] = action.payload or {}
        for candidate in self._derive_key_candidates(payload):
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
        try:
            numeric = int(key)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return str(key)
        return str(numeric)

    def _derive_key_candidates(self, payload: Mapping[str, object]) -> Sequence[object]:
        combos: list[object] = []
        combo = payload.get("combo")
        if combo:
            combos.append(combo)
        modifiers = payload.get("modifiers")
        base = payload.get("text") or payload.get("key")
        combo_string = self._format_combo(modifiers, base)
        if combo_string is not None:
            combos.append(combo_string)
        key_candidate = payload.get("key")
        text_candidate = payload.get("text")
        if key_candidate is not None:
            combos.append(key_candidate)
        if text_candidate is not None:
            combos.append(text_candidate)
        return tuple(combos)

    def _format_combo(self, modifiers: object, base: object) -> str | None:
        if not modifiers:
            return None
        try:
            modifier_value = int(modifiers)
        except (TypeError, ValueError):
            return None
        names = [name for flag, name in self._MODIFIER_FLAGS if modifier_value & flag]
        if not names:
            return None
        key_part: str | None
        if isinstance(base, str):
            key_part = base.strip().upper() or None
        elif isinstance(base, int) and 32 <= base <= 126:
            key_part = chr(base).upper()
        elif base is None:
            key_part = None
        else:
            key_part = str(base)
        if not key_part:
            return None
        names.append(key_part)
        return "+".join(names)


# Import built-in effects so they register with the global registry.
from . import ascii_snow as _ascii_snow  # noqa: E402,F401
from . import caps_roulette as _caps_roulette  # noqa: E402,F401
from . import cpu_heater as _cpu_heater  # noqa: E402,F401
from . import ctrl_alt_b_briefing as _ctrl_alt_b_briefing  # noqa: E402,F401
from . import ctrl_alt_k_ethics as _ctrl_alt_k_ethics  # noqa: E402,F401
from . import disk_full as _disk_full  # noqa: E402,F401
from . import fake_bsod as _fake_bsod  # noqa: E402,F401
from . import fake_exfil as _fake_exfil  # noqa: E402,F401
from . import fake_locker as _fake_locker  # noqa: E402,F401
from . import fake_update as _fake_update  # noqa: E402,F401
from . import force_close as _force_close  # noqa: E402,F401
from . import high_contrast as _high_contrast  # noqa: E402,F401
from . import invert_screen as _invert_screen  # noqa: E402,F401
from . import key_swap as _key_swap  # noqa: E402,F401
from . import lag_spike as _lag_spike  # noqa: E402,F401
from . import matrix_rain as _matrix_rain  # noqa: E402,F401
from . import matrix_shader as _matrix_shader  # noqa: E402,F401
from . import mock_keylogger as _mock_keylogger  # noqa: E402,F401
from . import mouse_gremlin as _mouse_gremlin  # noqa: E402,F401
from . import net_outage as _net_outage  # noqa: E402,F401
from . import popup_storm as _popup_storm  # noqa: E402,F401
from . import shame_bell as _shame_bell  # noqa: E402,F401
from . import terminal_storm as _terminal_storm  # noqa: E402,F401
from . import typer_gremlin as _typer_gremlin  # noqa: E402,F401
from . import uac_mirage as _uac_mirage  # noqa: E402,F401
from . import window_wobble as _window_wobble  # noqa: E402,F401
