from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from chaos_keyboard.audio import AudioManager
from chaos_keyboard.bus import EventBus, SystemAction


class DummyBackend:
    """Backend stub capturing playback requests for assertions."""

    def __init__(self) -> None:
        self.loaded_music: dict[str, object] = {}
        self.loaded_sfx: dict[str, object] = {}
        self.play_music_calls: list[tuple[object, bool]] = []
        self.stop_music_calls = 0
        self.play_sfx_calls: list[object] = []
        self.shutdown_called = False

    def load_music(self, path: Path) -> object:
        handle = f"music:{path.name}"
        self.loaded_music[path.name] = handle
        return handle

    def play_music(self, music: object, *, loop: bool = True) -> None:
        self.play_music_calls.append((music, loop))

    def stop_music(self) -> None:
        self.stop_music_calls += 1

    def load_sfx(self, path: Path) -> object:
        handle = f"sfx:{path.name}"
        self.loaded_sfx[path.name] = handle
        return handle

    def play_sfx(self, sfx: object) -> None:
        self.play_sfx_calls.append(sfx)

    def shutdown(self) -> None:
        self.shutdown_called = True


def _build_manager(bus: EventBus, backend: DummyBackend) -> AudioManager:
    asset_root = Path(__file__).resolve().parents[1] / "chaos_keyboard" / "assets" / "audio"
    return AudioManager(bus, asset_root=asset_root, backend_factory=lambda: backend)


def test_audio_state_controls_music_playback() -> None:
    bus = EventBus()
    backend = DummyBackend()
    manager = _build_manager(bus, backend)

    bus.publish(SystemAction(name="audio_state", payload={"enabled": True, "music": True, "sfx": True}))
    assert backend.play_music_calls, "Music should start when enabled."
    normal_handle = backend.loaded_music["music_loop.wav"]
    assert backend.play_music_calls[-1] == (normal_handle, True)

    bus.publish(SystemAction(name="audio_state", payload={"enabled": False, "music": True, "sfx": True}))
    assert backend.stop_music_calls == 1

    manager.close()
    assert backend.shutdown_called


def test_key_press_triggers_sfx_when_enabled() -> None:
    bus = EventBus()
    backend = DummyBackend()
    manager = _build_manager(bus, backend)

    bus.publish(SystemAction(name="audio_state", payload={"enabled": True, "music": True, "sfx": True}))
    backend.play_sfx_calls.clear()

    bus.publish(SystemAction(name="key_press", payload={}))
    assert backend.play_sfx_calls == [backend.loaded_sfx["key_bleep.wav"]]

    bus.publish(SystemAction(name="audio_state", payload={"enabled": True, "music": True, "sfx": False}))
    backend.play_sfx_calls.clear()
    bus.publish(SystemAction(name="key_press", payload={}))
    assert backend.play_sfx_calls == []

    manager.close()


def test_underwater_filter_switches_music_track() -> None:
    bus = EventBus()
    backend = DummyBackend()
    manager = _build_manager(bus, backend)

    bus.publish(SystemAction(name="audio_state", payload={"enabled": True, "music": True, "sfx": True}))
    backend.play_music_calls.clear()

    bus.publish(SystemAction(name="audio_filter", payload={"underwater": True}))
    underwater_handle = backend.loaded_music["music_underwater_loop.wav"]
    assert backend.play_music_calls == [(underwater_handle, True)]

    backend.play_music_calls.clear()
    bus.publish(SystemAction(name="audio_filter", payload={"underwater": False}))
    normal_handle = backend.loaded_music["music_loop.wav"]
    assert backend.play_music_calls == [(normal_handle, True)]

    manager.close()
