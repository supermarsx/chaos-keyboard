"""Chaos Keyboard application package."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .safety import (
    DEFAULT_MODE as DEFAULT_RUNTIME_MODE,
    LAB,
    SIM_ONLY,
    STREAM_SAFE,
    RuntimeMode,
    SafetyContext,
    SafetyInterlocks,
    SafetyWatchdog,
    normalize_mode,
)

__all__ = [
    "DEFAULT_MODE",
    "ensure_sim_only_mode",
    "RuntimeMode",
    "SafetyContext",
    "SafetyInterlocks",
    "SafetyWatchdog",
    "SIM_ONLY",
    "LAB",
    "STREAM_SAFE",
    "normalize_mode",
]

DEFAULT_MODE = DEFAULT_RUNTIME_MODE.value


def ensure_sim_only_mode(mode: str | None) -> str:
    """Return a safe runtime mode string.

    Parameters
    ----------
    mode:
        Preferred runtime mode name. If ``None`` or falsy the default
        simulation-only mode is returned. The helper normalises the string to
        uppercase and falls back to :data:`DEFAULT_MODE` whenever the provided
        value does not look like one of the recognised modes.
    """

    resolved = normalize_mode(mode)
    if resolved is LAB:
        return LAB.value
    if resolved is STREAM_SAFE:
        return STREAM_SAFE.value
    return DEFAULT_MODE


try:  # pragma: no cover - metadata lookup is trivial
    __version__ = version("chaos_keyboard")
except PackageNotFoundError:  # pragma: no cover - during development
    __version__ = "0.0.0"
