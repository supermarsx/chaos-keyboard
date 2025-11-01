"""Module entry-point so ``python -m chaos_keyboard`` launches the UI."""
from __future__ import annotations

import argparse
import sys

from . import ensure_sim_only_mode
from .app import main as run_app
from .config import (
    ConfigError,
    apply_cli_overrides,
    load_profiles,
    select_profile,
    set_active_profile,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the Chaos Keyboard UI")
    parser.add_argument(
        "--mode",
        default=None,
        help="Runtime mode to display (SIM ONLY, LAB, STREAM SAFE).",
    )
    parser.add_argument(
        "--preset",
        default=None,
        help="Configuration preset/profile to load.",
    )
    parser.add_argument(
        "--skin",
        default=None,
        help="Override the configured UI skin before startup.",
    )
    parser.add_argument(
        "--mute",
        action="store_true",
        help="Mute audio regardless of the profile setting.",
    )
    parser.add_argument(
        "--no-scanlines",
        action="store_true",
        help="Disable CRT scanlines even if the profile enables them.",
    )
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="Start the UI in fullscreen mode.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        profiles = load_profiles()
        profile = select_profile(args.preset, profiles)
        profile = apply_cli_overrides(profile, vars(args))
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    set_active_profile(profile)
    safe_mode = ensure_sim_only_mode(profile.safety.mode.value)
    return run_app(safe_mode, profile=profile)


if __name__ == "__main__":  # pragma: no cover - CLI hook
    sys.exit(main())
