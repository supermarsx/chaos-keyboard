"""Textual-based TUI entry point for Chaos Keyboard."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

from textual.app import App, ComposeResult
from textual.widgets import Button, Checkbox, Footer, Header, Static

from .bus import EventBus, SystemAction
from .config import ProfileConfig
from .effects import EffectController
from .logging import TelemetryLogger
from .safety import CapabilityNotAllowed, InterlockPending, SafetyContext


@dataclass
class _EffectStats:
    """Simple container tracking effect activity for the TUI."""

    active_effects: int = 0
    panic_count: int = 0


class ChaosKeyboardTUI(App):
    """Textual application exposing effect toggles and runtime stats."""

    BINDINGS = [
        ("p", "panic", "Panic"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        profile: ProfileConfig,
        *,
        bus: EventBus | None = None,
        safety: SafetyContext | None = None,
        effect_controller: EffectController | None = None,
        telemetry: TelemetryLogger | None = None,
    ) -> None:
        super().__init__()
        self._profile = profile
        self._bus = bus or EventBus()
        self._safety = safety or SafetyContext(profile.safety.mode)
        self._telemetry = telemetry
        self._effects = effect_controller or EffectController(
            self._safety,
            self._bus,
            telemetry=self._telemetry,
        )
        self._effect_state: Dict[str, bool] = {
            effect: False for effect in self._profile.effects.enabled
        }
        self._toggles: Dict[str, Checkbox] = {}
        self._stats_widget: Static | None = None
        self._help_widget: Static | None = None
        self._panic_button: Button | None = None
        self._stats = _EffectStats(active_effects=0, panic_count=0)
        self._active_effects: set[str] = set()
        self._unsubscribe = self._bus.subscribe(SystemAction, self._on_system_action)

    def compose(self) -> ComposeResult:
        """Compose the TUI layout."""

        yield Header(show_clock=True)
        summary = Static(
            f"Mode: {self._profile.safety.mode.value} | Skin: {self._profile.ui.skin}",
            id="profile-summary",
        )
        yield summary
        self._stats_widget = Static(self._format_stats(), id="effect-stats")
        yield self._stats_widget
        yield Static("Effects", id="effects-header")
        for effect in self._profile.effects.enabled:
            checkbox = Checkbox(effect, value=False, id=f"toggle-{effect}")
            self._toggles[effect] = checkbox
            yield checkbox
        self._panic_button = Button("PANIC", id="panic-button")
        yield self._panic_button
        self._help_widget = Static(self._keymap_help(), id="keymap-help")
        yield self._help_widget
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "panic-button":
            self._trigger_panic()
            event.stop()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        effect = event.checkbox.label.strip().lower()
        desired = bool(event.value)
        self._apply_effect_toggle(effect, desired)

    def action_panic(self) -> None:
        self._trigger_panic()

    def simulate_toggle(self, effect: str, enabled: bool) -> None:
        """Helper used in tests to toggle effects without UI events."""

        self._apply_effect_toggle(effect.strip().lower(), enabled)

    def stats(self) -> Mapping[str, int]:
        """Return a snapshot of current statistics."""

        return {
            "active_effects": self._stats.active_effects,
            "panic_count": self._stats.panic_count,
        }

    def teardown(self) -> None:
        """Release resources when the TUI exits."""

        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        if hasattr(self._effects, "close"):
            self._effects.close()

    def on_exit(self) -> None:
        self.teardown()

    def _trigger_panic(self) -> None:
        self._safety.panic()
        self._stats.panic_count += 1
        self._active_effects.clear()
        self._update_stats()
        self._bus.publish(SystemAction(name="panic_invoked", payload={"source": "tui"}))

    def _apply_effect_toggle(self, effect: str, enabled: bool) -> None:
        if effect not in self._effect_state:
            return
        self._bus.publish(
            SystemAction(
                name="effect_toggle_requested",
                payload={"effect": effect, "enabled": enabled},
            )
        )
        success = enabled
        try:
            if enabled:
                self._effects.start_effect(effect, source="tui")
            else:
                self._effects.stop_effect(effect)
        except CapabilityNotAllowed as exc:
            success = False
            self._bus.publish(
                SystemAction(
                    name="effect_toggle_denied",
                    payload={"effect": effect, "reason": str(exc)},
                )
            )
        except InterlockPending as exc:
            success = False
            self._bus.publish(
                SystemAction(
                    name="effect_interlock_pending",
                    payload={"effect": effect, "pending_steps": list(exc.pending_steps)},
                )
            )
        finally:
            self._effect_state[effect] = success
            toggle = self._toggles.get(effect)
            if toggle is not None:
                toggle.value = success
            if not success:
                self._active_effects.discard(effect)
            self._update_stats()

    def _on_system_action(self, action: SystemAction) -> None:
        payload = action.payload or {}
        if action.name == "effect_started":
            effect = str(payload.get("effect", "")).strip().lower()
            if effect:
                self._active_effects.add(effect)
                self._effect_state[effect] = True
                self._update_stats()
        elif action.name == "effect_stopped":
            effect = str(payload.get("effect", "")).strip().lower()
            if effect:
                self._active_effects.discard(effect)
                self._effect_state[effect] = False
                self._update_stats()

    def _update_stats(self) -> None:
        self._stats.active_effects = len(self._active_effects)
        if self._stats_widget is not None:
            self._stats_widget.update(self._format_stats())

    def _format_stats(self) -> str:
        return (
            f"Active effects: {self._stats.active_effects}"
            f" | Panic count: {self._stats.panic_count}"
        )

    def _keymap_help(self) -> str:
        return "F1-F12 trigger the classic effects. Ctrl+. activates the global panic." \
            " Press Q to quit."


def run(profile: ProfileConfig) -> int:
    """Launch the Textual TUI using ``profile``."""

    app = ChaosKeyboardTUI(profile)
    return app.run()
