"""Asset loading helpers for Chaos Keyboard."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

_PACKAGE_ROOT = Path(__file__).resolve().parent

__all__ = [
    "PACKAGE_ROOT",
    "iter_asset_paths",
    "resolve_asset",
]

PACKAGE_ROOT = _PACKAGE_ROOT


def iter_asset_paths() -> Iterable[Path]:
    """Yield the known asset directories that ship with the application."""

    for folder in ("audio", "sprites", "shaders"):
        yield _PACKAGE_ROOT / folder


def resolve_asset(*parts: str) -> Path:
    """Return the path to an asset bundled with the package.

    Parameters
    ----------
    *parts:
        Path components relative to the :mod:`chaos_keyboard.assets` package.
    """

    candidate = _PACKAGE_ROOT.joinpath(*parts)
    return candidate
