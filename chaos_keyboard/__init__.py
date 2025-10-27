"""Chaos Keyboard application package."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = [
    "DEFAULT_MODE",
    "ensure_sim_only_mode",
]

DEFAULT_MODE = "SIM ONLY"


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

    candidate = (mode or "").strip().upper()
    if candidate in {"SIM ONLY", "SIM", "SIMULATION"}:
        return DEFAULT_MODE
    if candidate in {"LAB", "LAB MODE", "LAB-ONLY"}:
        return "LAB"
    if candidate in {"STREAM", "STREAM SAFE", "SAFE"}:
        return "STREAM SAFE"
    return DEFAULT_MODE


try:  # pragma: no cover - metadata lookup is trivial
    __version__ = version("chaos_keyboard")
except PackageNotFoundError:  # pragma: no cover - during development
    __version__ = "0.0.0"
