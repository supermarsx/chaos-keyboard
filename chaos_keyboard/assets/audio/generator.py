"""Generate placeholder audio assets for Chaos Keyboard."""

from __future__ import annotations

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

_SAMPLE_RATE = 44100
_SAMPLE_WIDTH = 2  # bytes (16-bit)
_CHANNELS = 1


@dataclass(frozen=True)
class AudioAsset:
    """Descriptor for a generated audio asset."""

    filename: str
    builder: Callable[[Path], None]


def _write_wave(path: Path, samples: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(_CHANNELS)
        wav.setsampwidth(_SAMPLE_WIDTH)
        wav.setframerate(_SAMPLE_RATE)
        frames = bytearray()
        for sample in samples:
            clipped = max(-1.0, min(1.0, sample))
            frames.extend(struct.pack("<h", int(clipped * 32767)))
        wav.writeframes(bytes(frames))


def _sine_wave(
    frequency: float, duration: float, *, amplitude: float = 1.0
) -> list[float]:
    total_samples = int(duration * _SAMPLE_RATE)
    return [
        amplitude * math.sin(2.0 * math.pi * frequency * i / _SAMPLE_RATE)
        for i in range(total_samples)
    ]


def _apply_envelope(samples: list[float], attack: float, release: float) -> list[float]:
    total = len(samples)
    attack_samples = int(attack * _SAMPLE_RATE)
    release_samples = int(release * _SAMPLE_RATE)
    result: list[float] = []
    for index, value in enumerate(samples):
        if index < attack_samples:
            scale = index / max(1, attack_samples)
        elif index >= total - release_samples:
            scale = (total - index) / max(1, release_samples)
        else:
            scale = 1.0
        result.append(value * scale)
    return result


def _mix_tracks(*tracks: list[float]) -> list[float]:
    length = max((len(track) for track in tracks), default=0)
    mixed: list[float] = []
    for i in range(length):
        sample = 0.0
        for track in tracks:
            if i < len(track):
                sample += track[i]
        mixed.append(sample / max(1, len(tracks)))
    return mixed


def _generate_music_loop(path: Path) -> None:
    seconds = 4.0
    bass = _sine_wave(110.0, seconds, amplitude=0.6)
    harmony = _sine_wave(220.0, seconds, amplitude=0.3)
    melody = []
    beat_length = int(_SAMPLE_RATE * 0.5)
    pattern = [523.25, 659.25, 587.33, 659.25]
    while len(melody) < int(seconds * _SAMPLE_RATE):
        for note in pattern:
            melody.extend(_sine_wave(note, beat_length / _SAMPLE_RATE, amplitude=0.4))
    melody = melody[: int(seconds * _SAMPLE_RATE)]
    track = _mix_tracks(bass, harmony, melody)
    _write_wave(path, track)


def _generate_underwater_loop(path: Path) -> None:
    seconds = 4.0
    bass = _sine_wave(98.0, seconds, amplitude=0.7)
    pad = _sine_wave(147.0, seconds, amplitude=0.5)
    wobble = _sine_wave(4.0, seconds, amplitude=0.2)
    track = _mix_tracks(bass, pad)
    track = [sample * (0.7 + wobble[i]) for i, sample in enumerate(track)]
    _write_wave(path, track)


def _generate_key_bleep(path: Path) -> None:
    duration = 0.2
    wave_samples = _sine_wave(880.0, duration, amplitude=0.9)
    waved = _apply_envelope(wave_samples, attack=0.01, release=0.15)
    _write_wave(path, waved)


_ASSETS: tuple[AudioAsset, ...] = (
    AudioAsset("music_loop.wav", _generate_music_loop),
    AudioAsset("music_underwater_loop.wav", _generate_underwater_loop),
    AudioAsset("key_bleep.wav", _generate_key_bleep),
)


def audio_asset_filenames() -> tuple[str, ...]:
    """Return the filenames for all generated audio assets."""

    return tuple(asset.filename for asset in _ASSETS)


def ensure_audio_assets(output_dir: Path, *, force: bool = False) -> dict[str, Path]:
    """Ensure placeholder audio assets exist under *output_dir*."""

    output_dir.mkdir(parents=True, exist_ok=True)
    generated: dict[str, Path] = {}
    for asset in _ASSETS:
        target = output_dir / asset.filename
        if force or not target.exists():
            asset.builder(target)
        generated[asset.filename] = target
    return generated


def main() -> None:  # pragma: no cover - CLI helper
    ensure_audio_assets(Path(__file__).resolve().parent, force=True)


if __name__ == "__main__":  # pragma: no cover - CLI helper
    main()
