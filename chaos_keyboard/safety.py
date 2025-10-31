"""Safety policy and runtime mode helpers for Chaos Keyboard."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from threading import Event, Lock
from time import perf_counter
from typing import (
    Callable,
    FrozenSet,
    Iterable,
    MutableMapping,
    MutableSequence,
    Sequence,
)

__all__ = [
    "RuntimeMode",
    "SIM_ONLY",
    "LAB",
    "STREAM_SAFE",
    "DEFAULT_MODE",
    "SafetyError",
    "CapabilityNotAllowed",
    "SafetyInterlocks",
    "SafetyWatchdog",
    "SafetyContext",
    "InterlockPending",
    "normalize_mode",
]


logger = logging.getLogger(__name__)


class RuntimeMode(str, Enum):
    """Runtime modes that govern allowed capabilities."""

    SIM_ONLY = "SIM ONLY"
    LAB = "LAB"
    STREAM_SAFE = "STREAM SAFE"


SIM_ONLY: RuntimeMode = RuntimeMode.SIM_ONLY
LAB: RuntimeMode = RuntimeMode.LAB
STREAM_SAFE: RuntimeMode = RuntimeMode.STREAM_SAFE
DEFAULT_MODE: RuntimeMode = SIM_ONLY

_MODE_ALIASES: dict[str, RuntimeMode] = {
    "SIM": SIM_ONLY,
    "SIM ONLY": SIM_ONLY,
    "SIMULATION": SIM_ONLY,
    "SIM_ONLY": SIM_ONLY,
    "LAB MODE": LAB,
    "LAB-ONLY": LAB,
    "STREAM": STREAM_SAFE,
    "STREAM SAFE": STREAM_SAFE,
    "STREAM_SAFE": STREAM_SAFE,
    "SAFE": STREAM_SAFE,
}


def normalize_mode(mode: str | RuntimeMode | None) -> RuntimeMode:
    """Normalise user provided mode identifiers to :class:`RuntimeMode`."""

    if isinstance(mode, RuntimeMode):
        return mode
    candidate = (mode or "").strip().upper()
    if not candidate:
        return DEFAULT_MODE
    if candidate in _MODE_ALIASES:
        return _MODE_ALIASES[candidate]
    lookup_key = candidate.replace(" ", "_")
    return RuntimeMode.__members__.get(lookup_key, DEFAULT_MODE)


class SafetyError(RuntimeError):
    """Base exception raised when a safety policy is violated."""


class CapabilityNotAllowed(SafetyError):
    """Raised when an effect declares a capability not permitted in the mode."""


class InterlockPending(SafetyError):
    """Raised when an effect requires additional operator confirmations."""

    def __init__(self, effect: str, pending_steps: Sequence[str]) -> None:
        self.effect = effect
        self.pending_steps: tuple[str, ...] = tuple(pending_steps)
        description = ", ".join(self.pending_steps) or "unknown steps"
        super().__init__(
            f"Effect '{effect}' cannot start until interlock steps complete: {description}."
        )


@dataclass(slots=True)
class _DisruptiveInterlockState:
    """Track confirmation and hold state for disruptive effects."""

    require_double_confirm: bool = False
    confirmations: int = 0
    require_hold: bool = False
    hold_armed: bool = False
    hold_started_at: float | None = None
    active: bool = False

    def pending_steps(self, *, hold_duration: float) -> tuple[str, ...]:
        pending: list[str] = []
        if self.require_double_confirm and self.confirmations < 2:
            pending.append("double_confirm")
        if self.require_hold and not self.hold_armed:
            pending.append("hold_to_arm")
        return tuple(pending)

    def is_ready(self, *, hold_duration: float) -> bool:
        return not self.pending_steps(hold_duration=hold_duration)


@dataclass
class SafetyInterlocks:
    """Track operator-controlled interlocks for potentially dangerous modes."""

    lab_authorised: bool = False
    lab_token: str | None = None
    disruptive_effects: FrozenSet[str] = frozenset({"fake_bsod", "fake_locker"})
    hold_to_arm_effects: FrozenSet[str] = frozenset({"fake_bsod", "fake_locker"})
    hold_to_arm_duration: float = 1.5
    _disruptive_states: MutableMapping[str, _DisruptiveInterlockState] = field(
        default_factory=dict
    )

    def arm_lab_mode(self, token: str) -> None:
        """Enable lab mode access once the operator provides a token."""

        if not token:
            raise ValueError("A non-empty token is required to arm lab mode.")
        self.lab_authorised = True
        self.lab_token = token

    def disarm_lab_mode(self) -> None:
        """Disable lab mode access and clear the operator token."""

        self.lab_authorised = False
        self.lab_token = None
        self._disruptive_states.clear()

    def ensure_mode_allowed(self, mode: RuntimeMode) -> None:
        """Validate whether the requested mode can be activated."""

        if mode is LAB and not self.lab_authorised:
            raise SafetyError(
                "LAB mode requires operator authorisation; default builds remain in SIM ONLY."
            )

    def requires_disruptive_workflow(self, effect: str) -> bool:
        """Return ``True`` when ``effect`` requires disruptive confirmations."""

        return effect.strip().lower() in self.disruptive_effects

    def requires_hold_to_arm(self, effect: str) -> bool:
        """Return ``True`` if ``effect`` must satisfy hold-to-arm."""

        return effect.strip().lower() in self.hold_to_arm_effects

    def ensure_disruptive_interlocks(self, effect: str) -> None:
        """Raise when ``effect`` is not yet cleared for disruptive activation."""

        key = effect.strip().lower()
        if not self.requires_disruptive_workflow(key):
            return
        state = self._disruptive_states.setdefault(key, _DisruptiveInterlockState())
        state.require_double_confirm = True
        if self.requires_hold_to_arm(key):
            state.require_hold = True
        pending = state.pending_steps(hold_duration=self.hold_to_arm_duration)
        if pending:
            raise InterlockPending(key, pending)
        state.active = True

    def record_disruptive_confirmation(self, effect: str) -> tuple[str, ...]:
        """Record an operator confirmation for ``effect`` and return remaining steps."""

        key = effect.strip().lower()
        state = self._disruptive_states.setdefault(key, _DisruptiveInterlockState())
        state.require_double_confirm = True
        state.confirmations += 1
        return state.pending_steps(hold_duration=self.hold_to_arm_duration)

    def begin_hold_to_arm(self, effect: str) -> None:
        """Begin tracking a hold-to-arm interaction for ``effect``."""

        key = effect.strip().lower()
        state = self._disruptive_states.setdefault(key, _DisruptiveInterlockState())
        state.require_hold = True
        state.hold_started_at = perf_counter()
        state.hold_armed = False

    def complete_hold_to_arm(self, effect: str) -> bool:
        """Complete the hold-to-arm step and return whether it satisfied duration."""

        key = effect.strip().lower()
        state = self._disruptive_states.setdefault(key, _DisruptiveInterlockState())
        state.require_hold = True
        start = state.hold_started_at
        if start is None:
            raise SafetyError("Hold-to-arm was not initiated for this effect.")
        elapsed = perf_counter() - start
        state.hold_started_at = None
        state.hold_armed = elapsed >= self.hold_to_arm_duration
        return state.hold_armed

    def cancel_hold_to_arm(self, effect: str) -> None:
        """Abort an in-flight hold-to-arm interaction for ``effect``."""

        key = effect.strip().lower()
        state = self._disruptive_states.get(key)
        if state is None:
            return
        state.hold_started_at = None
        state.hold_armed = False

    def pending_disruptive_steps(self, effect: str) -> tuple[str, ...]:
        """Return outstanding steps before ``effect`` may activate."""

        key = effect.strip().lower()
        state = self._disruptive_states.setdefault(key, _DisruptiveInterlockState())
        if self.requires_disruptive_workflow(key):
            state.require_double_confirm = True
        if self.requires_hold_to_arm(key):
            state.require_hold = True
        return state.pending_steps(hold_duration=self.hold_to_arm_duration)

    def release_disruptive_effect(self, effect: str) -> None:
        """Reset interlock state once ``effect`` stops running."""

        key = effect.strip().lower()
        self._disruptive_states.pop(key, None)


class SafetyWatchdog:
    """Co-ordinate panic-stop callbacks and guarantee a quick shutdown."""

    def __init__(self, *, max_stop_duration: float = 0.2) -> None:
        self._max_stop_duration = max_stop_duration
        self._panic_event = Event()
        self._panic_complete = Event()
        self._panic_elapsed: float | None = None
        self._callbacks: MutableSequence[Callable[[], None]] = []
        self._lock = Lock()

    @property
    def max_stop_duration(self) -> float:
        """Return the maximum permitted delay for panic propagation."""

        return self._max_stop_duration

    def register(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Register a callback invoked when the panic button is pressed."""

        with self._lock:
            self._callbacks.append(callback)

        def unregister() -> None:
            with self._lock:
                try:
                    self._callbacks.remove(callback)
                except ValueError:
                    return

        return unregister

    def panic(self) -> None:
        """Trigger the panic button, stopping all effects immediately."""

        callbacks: Sequence[Callable[[], None]] | None = None
        with self._lock:
            if self._panic_event.is_set():
                should_wait = True
            else:
                should_wait = False
                self._panic_event.set()
                callbacks = list(self._callbacks)
                self._panic_complete.clear()
        if should_wait:
            # Ensure callers block until the initial panic completes.
            self._panic_complete.wait(self._max_stop_duration)
            return
        assert callbacks is not None  # Satisfy the type-checker; set when not waiting.
        start = perf_counter()
        try:
            for callback in callbacks:
                try:
                    callback()
                except Exception:  # noqa: BLE001 - continue stopping all effects
                    logger.exception(
                        "Safety panic callback %r raised an exception", callback
                    )
        finally:
            self._panic_elapsed = perf_counter() - start
            self._panic_complete.set()

    def wait_for_panic(self, timeout: float | None = None) -> bool:
        """Block until the panic button is triggered or ``timeout`` elapses."""

        deadline = timeout if timeout is not None else self._max_stop_duration
        start = perf_counter()
        fired = self._panic_complete.wait(deadline)
        if not fired:
            return False
        elapsed = perf_counter() - start
        # Fall back to measured elapsed time if panic completed faster than wait duration.
        panic_elapsed = self._panic_elapsed if self._panic_elapsed is not None else elapsed
        return panic_elapsed <= self._max_stop_duration + 1e-6

    def reset(self) -> None:
        """Clear the panic event; primarily used for testing."""

        self._panic_event.clear()
        self._panic_complete.clear()
        self._panic_elapsed = None


_MODE_CAPABILITIES: dict[RuntimeMode, FrozenSet[str]] = {
    SIM_ONLY: frozenset({"overlay", "audio", "ui"}),
    STREAM_SAFE: frozenset({"overlay", "audio", "ui", "censored_text"}),
    LAB: frozenset({
        "overlay",
        "audio",
        "ui",
        "censored_text",
        "system",
        "filesystem",
        "network",
    }),
}


class SafetyContext:
    """Runtime context injected into effects to consult policy decisions."""

    def __init__(
        self,
        mode: RuntimeMode | str | None = None,
        *,
        interlocks: SafetyInterlocks | None = None,
        watchdog: SafetyWatchdog | None = None,
    ) -> None:
        resolved_mode = normalize_mode(mode)
        interlock = interlocks or SafetyInterlocks()
        interlock.ensure_mode_allowed(resolved_mode)
        self._interlocks: SafetyInterlocks = interlock
        self._mode: RuntimeMode = resolved_mode
        self._watchdog: SafetyWatchdog = watchdog or SafetyWatchdog()

    @property
    def mode(self) -> RuntimeMode:
        """Return the active runtime mode."""

        return self._mode

    @property
    def watchdog(self) -> SafetyWatchdog:
        """Expose the watchdog responsible for panic propagation."""

        return self._watchdog

    @property
    def allowed_capabilities(self) -> FrozenSet[str]:
        """Set of capabilities that can be exercised in the current mode."""

        return _MODE_CAPABILITIES[self._mode]

    @property
    def interlocks(self) -> SafetyInterlocks:
        """Return the interlock configuration backing this context."""

        return self._interlocks

    def ensure_disruptive_interlocks(self, effect: str) -> None:
        """Ensure disruptive interlocks are satisfied before activation."""

        self._interlocks.ensure_disruptive_interlocks(effect)

    def record_disruptive_confirmation(self, effect: str) -> tuple[str, ...]:
        """Record one operator confirmation for ``effect``."""

        return self._interlocks.record_disruptive_confirmation(effect)

    def begin_hold_to_arm(self, effect: str) -> None:
        """Mark that the operator started holding the arm control for ``effect``."""

        self._interlocks.begin_hold_to_arm(effect)

    def complete_hold_to_arm(self, effect: str) -> bool:
        """Complete the hold-to-arm interaction for ``effect``."""

        return self._interlocks.complete_hold_to_arm(effect)

    def allows(self, capability: str) -> bool:
        """Return ``True`` if ``capability`` is permitted in this mode."""

        return capability in self.allowed_capabilities

    def require_capability(self, capability: str) -> None:
        """Ensure a single capability is permitted; raise when denied."""

        self.require_capabilities([capability])

    def require_capabilities(self, capabilities: Iterable[str]) -> None:
        """Ensure all requested capabilities are permitted; raise if not."""

        for capability in capabilities:
            if capability not in self.allowed_capabilities:
                raise CapabilityNotAllowed(
                    f"Capability '{capability}' is not permitted in {self._mode.value}."
                )

    def panic(self) -> None:
        """Trigger the panic stop to halt all effects immediately."""

        self._watchdog.panic()
