"""TOML configuration parser for Chaos Keyboard profiles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from ..safety import RuntimeMode, normalize_mode


class ConfigError(ValueError):
    """Raised when a configuration profile cannot be parsed."""


@dataclass(frozen=True)
class UISettings:
    """Presentation settings for the UI layer."""

    skin: str
    scanlines: bool
    fullscreen: bool


@dataclass(frozen=True)
class AudioSettings:
    """Audio playback settings for the runtime."""

    enabled: bool
    music: bool
    sfx: bool


@dataclass(frozen=True)
class SafetySettings:
    """Safety mode applied before the UI boots."""

    mode: RuntimeMode


@dataclass(frozen=True)
class EffectSettings:
    """Effect availability configuration."""

    enabled: tuple[str, ...]


@dataclass(frozen=True)
class LimitSettings:
    """Runtime limits for resource intensive features."""

    max_popups: int
    cpu_ms: int


@dataclass(frozen=True)
class ProfileConfig:
    """Fully parsed configuration profile."""

    name: str
    ui: UISettings
    audio: AudioSettings
    safety: SafetySettings
    effects: EffectSettings
    limits: LimitSettings


def parse_profiles(document: Mapping[str, object]) -> dict[str, ProfileConfig]:
    """Parse all profiles declared in a TOML document."""

    raw_profiles = _expect_mapping(document, "profiles")
    parsed: dict[str, ProfileConfig] = {}
    for name, profile_data in raw_profiles.items():
        if not isinstance(profile_data, Mapping):
            raise ConfigError(f"Profile '{name}' must be a table of settings.")
        profile_name = str(name)
        ui = _parse_ui(profile_data.get("ui"))
        audio = _parse_audio(profile_data.get("audio"))
        safety = _parse_safety(profile_data.get("safety"))
        effects = _parse_effects(profile_data.get("effects"))
        limits = _parse_limits(profile_data.get("limits"))
        parsed[profile_name] = ProfileConfig(
            name=profile_name,
            ui=ui,
            audio=audio,
            safety=safety,
            effects=effects,
            limits=limits,
        )
    if not parsed:
        raise ConfigError("At least one profile must be declared in the configuration.")
    return parsed


def _parse_ui(section: object) -> UISettings:
    table = _as_mapping(section, "ui")
    skin = str(table.get("skin", "crt")).strip() or "crt"
    scanlines = bool(table.get("scanlines", True))
    fullscreen = bool(table.get("fullscreen", False))
    return UISettings(skin=skin, scanlines=scanlines, fullscreen=fullscreen)


def _parse_audio(section: object) -> AudioSettings:
    table = _as_mapping(section, "audio")
    enabled = bool(table.get("enabled", True))
    music = bool(table.get("music", True))
    sfx = bool(table.get("sfx", True))
    return AudioSettings(enabled=enabled, music=music, sfx=sfx)


def _parse_safety(section: object) -> SafetySettings:
    table = _as_mapping(section, "safety")
    mode_value = table.get("mode")
    mode = normalize_mode(mode_value)
    return SafetySettings(mode=mode)


def _parse_effects(section: object) -> EffectSettings:
    table = _as_mapping(section, "effects")
    enabled_raw = table.get("enabled", ())
    if isinstance(enabled_raw, str):
        enabled_values: Sequence[str] = (enabled_raw,)
    elif isinstance(enabled_raw, Iterable):
        enabled_values = tuple(str(value).strip().lower() for value in enabled_raw)
    else:
        raise ConfigError("effects.enabled must be a list of effect identifiers.")
    return EffectSettings(enabled=tuple(enabled_values))


def _parse_limits(section: object) -> LimitSettings:
    table = _as_mapping(section, "limits")
    max_popups = int(table.get("max_popups", 48))
    cpu_ms = int(table.get("cpu_ms", 250))
    return LimitSettings(max_popups=max_popups, cpu_ms=cpu_ms)


def _expect_mapping(document: Mapping[str, object], key: str) -> Mapping[str, object]:
    try:
        value = document[key]
    except KeyError as exc:
        raise ConfigError(f"Configuration missing required section '{key}'.") from exc
    if not isinstance(value, Mapping):
        raise ConfigError(f"Section '{key}' must be a table of values.")
    return value


def _as_mapping(section: object, key: str) -> Mapping[str, object]:
    if section is None:
        return {}
    if not isinstance(section, Mapping):
        raise ConfigError(f"Section '{key}' must be a table of values.")
    return section
