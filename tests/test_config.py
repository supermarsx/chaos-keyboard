from __future__ import annotations

import argparse

import pytest

from chaos_keyboard.config import (
    active_profile,
    ConfigError,
    apply_cli_overrides,
    clear_active_profile,
    load_profiles,
    select_profile,
    set_active_profile,
)
from chaos_keyboard.config.parser import ProfileConfig
from chaos_keyboard.safety import RuntimeMode


@pytest.fixture(autouse=True)
def clear_active_profile_fixture() -> None:
    clear_active_profile()
    yield
    clear_active_profile()


def _load_default_profile() -> ProfileConfig:
    profiles = load_profiles()
    return select_profile(None, profiles)


def test_load_default_profile() -> None:
    profile = _load_default_profile()
    assert profile.ui.skin == "crt"
    assert profile.audio.enabled is True
    assert profile.safety.mode is RuntimeMode.SIM_ONLY
    assert "fake_bsod" in profile.effects.enabled
    assert profile.limits.max_popups == 48
    assert profile.limits.cpu_ms == 250


def test_cli_overrides_merge() -> None:
    profile = _load_default_profile()
    args = argparse.Namespace(
        mode="stream_safe",
        skin="dmg_boy",
        mute=True,
        no_scanlines=True,
        fullscreen=True,
        preset=None,
    )
    updated = apply_cli_overrides(profile, vars(args))
    assert updated.ui.skin == "dmg_boy"
    assert updated.ui.scanlines is False
    assert updated.ui.fullscreen is True
    assert updated.audio.enabled is False
    assert updated.safety.mode is RuntimeMode.STREAM_SAFE


def test_set_active_profile_roundtrip() -> None:
    profile = _load_default_profile()
    set_active_profile(profile)
    retrieved = active_profile()
    assert retrieved is profile


def test_select_unknown_profile_raises() -> None:
    profiles = load_profiles()
    with pytest.raises(ConfigError):
        select_profile("missing", profiles)
