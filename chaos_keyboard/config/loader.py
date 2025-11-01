"""Configuration profile loader for Chaos Keyboard."""
from __future__ import annotations

from dataclasses import asdict, replace
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Iterable, Mapping

import tomllib

from .parser import (
    ConfigError,
    ProfileConfig,
    parse_profiles,
)
from ..safety import normalize_mode

DEFAULT_PROFILE_NAME = "default"
_DEFAULT_RESOURCE = resources.files(__package__).joinpath("default.toml")


def load_profiles(*, extra_paths: Iterable[Path] | None = None) -> dict[str, ProfileConfig]:
    """Load profiles from the packaged defaults and optional overrides."""

    merged: dict[str, object] = {}
    sources = list(_iter_sources(extra_paths))
    for path in sources:
        content = _read_text(path)
        if content is None:
            continue
        data = tomllib.loads(content)
        merged = _deep_merge(merged, data)
    return parse_profiles(merged)


def select_profile(name: str | None, profiles: Mapping[str, ProfileConfig]) -> ProfileConfig:
    """Select ``name`` from ``profiles`` with a sensible default."""

    profile_name = name or DEFAULT_PROFILE_NAME
    try:
        return profiles[profile_name]
    except KeyError as exc:
        available = ", ".join(sorted(profiles)) or "<none>"
        raise ConfigError(
            f"Unknown profile '{profile_name}'. Available profiles: {available}."
        ) from exc


def apply_cli_overrides(profile: ProfileConfig, args: Mapping[str, object]) -> ProfileConfig:
    """Merge CLI arguments into ``profile`` returning a new profile instance."""

    updated = profile
    mode_arg = args.get("mode")
    if mode_arg:
        normalized = normalize_mode(str(mode_arg))
        updated = replace(updated, safety=replace(updated.safety, mode=normalized))
    skin = args.get("skin")
    if skin:
        skin_str = str(skin).strip() or updated.ui.skin
        updated = replace(updated, ui=replace(updated.ui, skin=skin_str))
    if args.get("no_scanlines"):
        updated = replace(updated, ui=replace(updated.ui, scanlines=False))
    if args.get("fullscreen"):
        updated = replace(updated, ui=replace(updated.ui, fullscreen=True))
    if args.get("mute"):
        updated = replace(updated, audio=replace(updated.audio, enabled=False))
    return updated


def profile_payload(profile: ProfileConfig) -> dict[str, object]:
    """Return a serialisable payload describing ``profile`` for telemetry."""

    payload = {
        "name": profile.name,
        "ui": asdict(profile.ui),
        "audio": asdict(profile.audio),
        "safety": {"mode": profile.safety.mode.value},
        "effects": {"enabled": list(profile.effects.enabled)},
        "limits": asdict(profile.limits),
    }
    return payload


def _deep_merge(base: Mapping[str, object], override: Mapping[str, object]) -> dict[str, object]:
    result: dict[str, object] = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, Mapping):
            result[key] = _deep_merge(result[key], value)
            continue
        if isinstance(value, Mapping):
            result[key] = dict(value)
        else:
            result[key] = value
    return result


_active_profile: ProfileConfig | None = None


def set_active_profile(profile: ProfileConfig) -> None:
    """Record ``profile`` as the active runtime configuration."""

    global _active_profile
    _active_profile = profile


def active_profile() -> ProfileConfig:
    """Return the currently active profile or raise when unset."""

    if _active_profile is None:
        raise ConfigError("No active profile has been configured yet.")
    return _active_profile


def clear_active_profile() -> None:
    """Clear the active profile; primarily used by tests."""

    global _active_profile
    _active_profile = None


def _iter_sources(extra_paths: Iterable[Path] | None) -> Iterable[Traversable | Path]:
    yield _DEFAULT_RESOURCE
    if extra_paths is None:
        return
    for path in extra_paths:
        yield Path(path)


def _read_text(path: Traversable | Path) -> str | None:
    if isinstance(path, Path):
        if not path.exists() or not path.is_file():
            return None
        return path.read_text(encoding="utf-8")
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")
