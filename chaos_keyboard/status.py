"""Pure state models for the ModeStatusBar widget."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .bus import SystemAction

__all__ = ["StatusIndicators"]


@dataclass(slots=True)
class StatusIndicators:
    """Track active effects and frame timing for the status bar."""

    active_effects: list[str] = field(default_factory=list)
    fps: float | None = None

    def handle_system_action(self, action: SystemAction) -> bool:
        """Ingest a :class:`~chaos_keyboard.bus.SystemAction` update."""

        payload = action.payload
        if action.name == "effect_started":
            return self._record_effect(payload, started=True)
        if action.name == "effect_stopped":
            return self._record_effect(payload, started=False)
        if action.name == "frame_timing":
            return self._record_frame_timing(payload)
        return False

    def effects_chip(self) -> str:
        """Return a formatted representation of the active effects."""

        if not self.active_effects:
            return "Effects: NONE"
        chips = " ".join(f"▣ {name}" for name in self.active_effects)
        return f"Effects: {chips}"

    def fps_chip(self) -> str:
        """Return the formatted frames-per-second display."""

        if self.fps is None:
            return "FPS: --"
        return f"FPS: {self.fps:.1f}"

    def reset(self) -> None:
        """Clear tracked state."""

        self.active_effects.clear()
        self.fps = None

    def _record_effect(
        self, payload: Mapping[str, object] | None, *, started: bool
    ) -> bool:
        effect = self._extract_effect_name(payload)
        if effect is None:
            return False
        normalised = effect.upper()
        if started:
            if normalised in self.active_effects:
                return False
            self.active_effects.append(normalised)
            self.active_effects.sort()
            return True
        if normalised not in self.active_effects:
            return False
        self.active_effects.remove(normalised)
        return True

    def _record_frame_timing(self, payload: Mapping[str, object] | None) -> bool:
        fps_value = self._extract_fps(payload)
        if fps_value is None:
            return False
        if self.fps is not None and abs(self.fps - fps_value) < 1e-3:
            return False
        self.fps = fps_value
        return True

    @staticmethod
    def _extract_effect_name(payload: Mapping[str, object] | None) -> str | None:
        if payload is None:
            return None
        value = payload.get("effect")
        if isinstance(value, str):
            candidate = value.strip()
            if candidate:
                return candidate
        return None

    @staticmethod
    def _extract_fps(payload: Mapping[str, object] | None) -> float | None:
        if payload is None:
            return None
        value = payload.get("fps")
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
