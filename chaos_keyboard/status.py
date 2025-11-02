"""Pure state models for the ModeStatusBar widget."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .bus import SystemAction
from .safety import LAB, SIM_ONLY, STREAM_SAFE, RuntimeMode, normalize_mode

__all__ = ["ChipMeta", "StatusIndicators"]


@dataclass(frozen=True, slots=True)
class ChipMeta:
    """Describe how a status chip should be rendered."""

    label: str
    value: str
    state: str
    tooltip: str | None = None

    @property
    def text(self) -> str:
        """Return a human-readable label suitable for a Qt :class:`QLabel`."""

        return f"{self.label}: {self.value}"


_MODE_STATES: dict[RuntimeMode, str] = {
    SIM_ONLY: "mode-sim",
    STREAM_SAFE: "mode-stream",
    LAB: "mode-lab",
}

_MODE_TOOLTIPS: dict[RuntimeMode, str] = {
    SIM_ONLY: "Simulation-only mode – all chaos is cosmetic.",
    STREAM_SAFE: "Stream Safe mode – toned-down visuals and messaging.",
    LAB: "Lab mode – requires operator authorisation and safeguards.",
}


@dataclass(slots=True)
class StatusIndicators:
    """Track active effects, runtime mode, and frame timing for the status bar."""

    active_effects: list[str] = field(default_factory=list)
    fps: float | None = None
    mode: RuntimeMode = SIM_ONLY

    def handle_system_action(self, action: SystemAction) -> bool:
        """Ingest a :class:`~chaos_keyboard.bus.SystemAction` update."""

        payload = action.payload
        if action.name == "effect_started":
            return self._record_effect(payload, started=True)
        if action.name == "effect_stopped":
            return self._record_effect(payload, started=False)
        if action.name == "frame_timing":
            return self._record_frame_timing(payload)
        if action.name == "runtime_mode":
            return self._record_mode(payload)
        if action.name == "panic_invoked":
            return self._handle_panic()
        return False

    def set_mode(self, mode: RuntimeMode | str) -> bool:
        """Set the runtime mode, returning ``True`` when it changes."""

        if isinstance(mode, RuntimeMode):
            resolved = mode
        else:
            resolved = normalize_mode(mode)
        if self.mode is resolved:
            return False
        self.mode = resolved
        return True

    def mode_chip(self) -> ChipMeta:
        """Return chip metadata describing the current runtime mode."""

        state = _MODE_STATES.get(self.mode, "mode-unknown")
        tooltip = _MODE_TOOLTIPS.get(self.mode)
        return ChipMeta(label="Mode", value=self.mode.value, state=state, tooltip=tooltip)

    def effects_chip(self) -> ChipMeta:
        """Return chip metadata describing active effects."""

        if not self.active_effects:
            return ChipMeta(label="Effects", value="NONE", state="effects-idle")
        chips = " ".join(f"▣ {name}" for name in self.active_effects)
        return ChipMeta(label="Effects", value=chips, state="effects-active")

    def fps_chip(self) -> ChipMeta:
        """Return chip metadata describing the current frames-per-second reading."""

        if self.fps is None:
            return ChipMeta(label="FPS", value="--", state="fps-idle")
        return ChipMeta(label="FPS", value=f"{self.fps:.1f}", state="fps-active")

    def reset(self) -> None:
        """Clear tracked state except for the runtime mode."""

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

    def _record_mode(self, payload: Mapping[str, object] | None) -> bool:
        mode = self._extract_mode(payload)
        if mode is None:
            return False
        if self.mode is mode:
            return False
        self.mode = mode
        return True

    def _handle_panic(self) -> bool:
        changed = bool(self.active_effects or self.fps is not None)
        self.reset()
        return changed

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

    @staticmethod
    def _extract_mode(payload: Mapping[str, object] | None) -> RuntimeMode | None:
        if payload is None:
            return None
        value = payload.get("mode")
        if isinstance(value, RuntimeMode):
            return value
        if isinstance(value, str) and value.strip():
            return normalize_mode(value)
        return None
