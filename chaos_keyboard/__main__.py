"""Module entry-point so ``python -m chaos_keyboard`` launches the UI."""
from __future__ import annotations

import argparse
import sys

from . import DEFAULT_MODE, ensure_sim_only_mode
from .app import main as run_app


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the Chaos Keyboard UI")
    parser.add_argument(
        "--mode",
        default=DEFAULT_MODE,
        help="Runtime mode to display (SIM ONLY, LAB, STREAM SAFE). Default: %(default)s",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    safe_mode = ensure_sim_only_mode(args.mode)
    return run_app(safe_mode)


if __name__ == "__main__":  # pragma: no cover - CLI hook
    sys.exit(main())
