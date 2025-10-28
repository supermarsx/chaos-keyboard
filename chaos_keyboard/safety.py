"""Safety policy and runtime mode helpers for Chaos Keyboard."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import Event, Lock
from time import perf_counter
from typing import Callable, FrozenSet, Iterable, MutableSequence, Sequence

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
    "normalize_mode",
]


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


@dataclass
class SafetyInterlocks:
    """Track operator-controlled interlocks for potentially dangerous modes."""

    lab_authorised: bool = False
    lab_token: str | None = None

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

    def ensure_mode_allowed(self, mode: RuntimeMode) -> None:
        """Validate whether the requested mode can be activated."""

        if mode is LAB and not self.lab_authorised:
            raise SafetyError(
                "LAB mode requires operator authorisation; default builds remain in SIM ONLY."
            )


class SafetyWatchdog:
    """Co-ordinate panic-stop callbacks and guarantee a quick shutdown."""

    def __init__(self, *, max_stop_duration: float = 0.2) -> None:
        self._max_stop_duration = max_stop_duration
        self._panic_event = Event()
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

        if self._panic_event.is_set():
            return
        self._panic_event.set()
        with self._lock:
            callbacks: Sequence[Callable[[], None]] = list(self._callbacks)
        for callback in callbacks:
            callback()

    def wait_for_panic(self, timeout: float | None = None) -> bool:
        """Block until the panic button is triggered or ``timeout`` elapses."""

        deadline = timeout if timeout is not None else self._max_stop_duration
        start = perf_counter()
        fired = self._panic_event.wait(deadline)
        if not fired:
            return False
        elapsed = perf_counter() - start
        return elapsed <= self._max_stop_duration + 1e-6

    def reset(self) -> None:
        """Clear the panic event; primarily used for testing."""

        self._panic_event.clear()


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
