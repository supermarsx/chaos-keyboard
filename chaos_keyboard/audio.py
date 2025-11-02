"""Runtime audio manager for Chaos Keyboard."""
from __future__ import annotations

import importlib
import importlib.util
import threading
from pathlib import Path
from typing import Callable, Dict, Optional, Protocol

from .bus import EventBus, SystemAction
from .assets.audio.generator import ensure_audio_assets


class AudioBackend(Protocol):
    """Protocol describing the operations required by :class:`AudioManager`."""

    def load_music(self, path: Path) -> object:
        """Load a music asset and return an opaque handle."""

    def play_music(self, music: object, *, loop: bool = True) -> None:
        """Begin playback of a music asset."""

    def stop_music(self) -> None:
        """Stop any active music playback."""

    def load_sfx(self, path: Path) -> object:
        """Load a sound effect asset and return an opaque handle."""

    def play_sfx(self, sfx: object) -> None:
        """Play a one-shot sound effect."""

    def shutdown(self) -> None:
        """Release any resources held by the backend."""


class SilentAudioBackend:
    """Fallback backend used when no audio engine is available."""

    def __init__(self) -> None:
        self.played_music: list[tuple[object, bool]] = []
        self.played_sfx: list[object] = []
        self.stopped_music: int = 0

    def load_music(self, path: Path) -> object:
        return path

    def play_music(self, music: object, *, loop: bool = True) -> None:
        self.played_music.append((music, loop))

    def stop_music(self) -> None:
        self.stopped_music += 1

    def load_sfx(self, path: Path) -> object:
        return path

    def play_sfx(self, sfx: object) -> None:
        self.played_sfx.append(sfx)

    def shutdown(self) -> None:  # pragma: no cover - trivial
        return


class PygameMixerBackend:
    """Audio backend powered by :mod:`pygame.mixer`."""

    def __init__(self) -> None:
        pygame_module = importlib.import_module("pygame")
        self._pygame = pygame_module
        if not self._pygame.mixer.get_init():  # pragma: no cover - dependent on runtime
            self._pygame.mixer.init()
        self._loaded_music: Path | None = None
        self._sfx_cache: Dict[Path, "pygame.mixer.Sound"] = {}

    def load_music(self, path: Path) -> object:
        return path

    def play_music(self, music: object, *, loop: bool = True) -> None:
        path = Path(music)
        if self._loaded_music != path:
            self._pygame.mixer.music.load(str(path))
            self._loaded_music = path
        loops = -1 if loop else 0
        self._pygame.mixer.music.play(loops=loops)

    def stop_music(self) -> None:
        self._pygame.mixer.music.stop()

    def load_sfx(self, path: Path) -> object:
        cached = self._sfx_cache.get(path)
        if cached is not None:
            return cached
        sound = self._pygame.mixer.Sound(str(path))
        self._sfx_cache[path] = sound
        return sound

    def play_sfx(self, sfx: object) -> None:
        sound = sfx  # type: ignore[assignment]
        sound.play()

    def shutdown(self) -> None:  # pragma: no cover - dependent on runtime
        self._pygame.mixer.quit()


class SimpleAudioBackend:
    """Audio backend relying on :mod:`simpleaudio` for playback."""

    def __init__(self) -> None:
        simpleaudio_module = importlib.import_module("simpleaudio")
        self._simpleaudio = simpleaudio_module
        self._music_thread: threading.Thread | None = None
        self._music_lock = threading.Lock()
        self._music_stop = threading.Event()
        self._music_wave: object | None = None
        self._loop_music = True

    def load_music(self, path: Path) -> object:
        return self._simpleaudio.WaveObject.from_wave_file(str(path))

    def play_music(self, music: object, *, loop: bool = True) -> None:
        with self._music_lock:
            self._music_wave = music
            self._loop_music = loop
            self._music_stop.clear()
            if self._music_thread is None or not self._music_thread.is_alive():
                self._music_thread = threading.Thread(
                    target=self._run_loop,
                    name="ChaosKeyboardMusicLoop",
                    daemon=True,
                )
                self._music_thread.start()

    def stop_music(self) -> None:
        self._music_stop.set()
        thread = self._music_thread
        if thread is not None:
            thread.join(timeout=0.1)
        self._music_thread = None

    def load_sfx(self, path: Path) -> object:
        return self._simpleaudio.WaveObject.from_wave_file(str(path))

    def play_sfx(self, sfx: object) -> None:
        wave = sfx  # type: ignore[assignment]
        wave.play()

    def shutdown(self) -> None:
        self.stop_music()

    def _run_loop(self) -> None:
        while not self._music_stop.is_set():
            with self._music_lock:
                wave = self._music_wave
                loop = self._loop_music
            if wave is None:
                break
            playback = wave.play()
            playback.wait_done()
            if not loop:
                break


def _detect_backend() -> AudioBackend:
    if importlib.util.find_spec("pygame") is not None:
        return PygameMixerBackend()
    if importlib.util.find_spec("simpleaudio") is not None:
        return SimpleAudioBackend()
    return SilentAudioBackend()


class AudioManager:
    """High-level audio controller reacting to system events."""

    def __init__(
        self,
        bus: EventBus,
        *,
        asset_root: Path | None = None,
        backend_factory: Callable[[], AudioBackend] | None = None,
    ) -> None:
        self._bus = bus
        self._asset_root = asset_root or Path(__file__).resolve().parent / "assets" / "audio"
        self._backend_factory = backend_factory or _detect_backend
        ensure_audio_assets(self._asset_root)
        self._backend = self._backend_factory()
        self._music_enabled = True
        self._sfx_enabled = True
        self._audio_enabled = True
        self._underwater = False
        self._music_handles: Dict[str, object] = {}
        self._sfx_handles: Dict[str, object] = {}
        self._current_music: Optional[str] = None
        self._system_unsubscribe = self._bus.subscribe(SystemAction, self._on_system_action)
        self._load_assets()

    def close(self) -> None:
        """Release backend resources and unsubscribe from the bus."""

        if self._system_unsubscribe is not None:
            self._system_unsubscribe()
            self._system_unsubscribe = None
        self._backend.stop_music()
        self._backend.shutdown()

    def _load_assets(self) -> None:
        music_files = {
            "normal": "music_loop.wav",
            "underwater": "music_underwater_loop.wav",
        }
        sfx_files = {"key_press": "key_bleep.wav"}
        for key, filename in music_files.items():
            path = self._asset_root / filename
            if path.exists():
                self._music_handles[key] = self._backend.load_music(path)
        for key, filename in sfx_files.items():
            path = self._asset_root / filename
            if path.exists():
                self._sfx_handles[key] = self._backend.load_sfx(path)

    def _on_system_action(self, action: SystemAction) -> None:
        if action.name == "audio_state":
            self._handle_audio_state(action.payload or {})
        elif action.name == "key_press":
            self._handle_key_press()
        elif action.name == "audio_filter":
            self._handle_audio_filter(action.payload or {})

    def _handle_audio_state(self, payload: Dict[str, object]) -> None:
        self._audio_enabled = bool(payload.get("enabled", True))
        self._music_enabled = bool(payload.get("music", True))
        self._sfx_enabled = bool(payload.get("sfx", True))
        self._apply_music_state()

    def _handle_key_press(self) -> None:
        if not (self._audio_enabled and self._sfx_enabled):
            return
        sfx = self._sfx_handles.get("key_press")
        if sfx is None:
            return
        self._backend.play_sfx(sfx)

    def _handle_audio_filter(self, payload: Dict[str, object]) -> None:
        underwater = bool(payload.get("underwater"))
        if underwater == self._underwater:
            return
        self._underwater = underwater
        self._apply_music_state()

    def _apply_music_state(self) -> None:
        if not (self._audio_enabled and self._music_enabled):
            if self._current_music is not None:
                self._backend.stop_music()
                self._current_music = None
            return
        desired = "underwater" if self._underwater else "normal"
        handle = self._music_handles.get(desired)
        if handle is None:
            return
        self._backend.play_music(handle, loop=True)
        self._current_music = desired


__all__ = ["AudioManager", "AudioBackend", "SilentAudioBackend"]
