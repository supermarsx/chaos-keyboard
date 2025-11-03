"""Pipeline entrypoint for generating placeholder audio assets."""

from __future__ import annotations

from pathlib import Path

from chaos_keyboard.assets.audio.generator import ensure_audio_assets


def run(output_dir: Path | None = None, *, force: bool = True) -> dict[str, Path]:
    """Generate audio assets and return a mapping of filenames to paths."""

    default_root = (
        Path(__file__).resolve().parents[1] / "chaos_keyboard" / "assets" / "audio"
    )
    target = output_dir or default_root
    return ensure_audio_assets(target, force=force)


def main() -> None:  # pragma: no cover - CLI helper
    assets = run()
    for name, path in assets.items():
        print(f"Generated {name} at {path}")


if __name__ == "__main__":  # pragma: no cover - CLI helper
    main()
