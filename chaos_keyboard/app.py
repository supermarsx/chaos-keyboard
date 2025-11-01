"""Core Qt application scaffolding for Chaos Keyboard."""
from __future__ import annotations

import sys
from typing import ClassVar, Tuple

from . import DEFAULT_MODE, ensure_sim_only_mode
from .bus import EventBus, SystemAction, VisualAction
from .config import ConfigError, ProfileConfig, active_profile, profile_payload
from .console import ConsoleBuffer
from .effects import EffectController
from .logging import TelemetryLogger
from .safety import SafetyContext
from .status import StatusIndicators

try:  # pragma: no cover - import side effect
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QCloseEvent, QKeyEvent
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QGridLayout,
        QLabel,
        QMainWindow,
        QPlainTextEdit,
        QPushButton,
        QSizePolicy,
        QScrollBar,
        QSplitter,
        QStatusBar,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - handled at runtime
    raise ModuleNotFoundError(
        "PySide6 must be installed to run the Chaos Keyboard UI."
    ) from exc


class KeyboardGrid(QFrame):
    """Placeholder widget representing the retro keyboard layout."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("keyboardGrid")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        layout = QGridLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 12, 12, 12)

        label = QLabel("Keyboard Grid\n(placeholder)")
        label.setAlignment(Qt.AlignCenter)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(label, 0, 0)


class CrackConsolePanel(QFrame):
    """Animated console view subscribing to visual bus events."""

    TICK_INTERVAL_MS = 32

    def __init__(
        self,
        bus: EventBus,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("crackConsole")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Sunken)
        self.setStyleSheet(
            "#crackConsole {"
            "background-color: #050810;"
            "border: 2px solid #14422e;"
            "color: #39ff14;"
            "}"
        )

        self._bus = bus
        self._buffer = ConsoleBuffer()
        self._unsubscribe = bus.subscribe(VisualAction, self._on_visual_action)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QLabel("CRACK CONSOLE")
        header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setObjectName("crackConsoleHeader")
        header.setStyleSheet(
            "#crackConsoleHeader {"
            "font-weight: 700;"
            "letter-spacing: 2px;"
            "color: #6bff5c;"
            "}"
        )

        self._text_area = QPlainTextEdit(self)
        self._text_area.setObjectName("crackConsoleText")
        self._text_area.setReadOnly(True)
        self._text_area.setLineWrapMode(QPlainTextEdit.NoWrap)
        self._text_area.setFrameStyle(QFrame.NoFrame)
        self._text_area.setStyleSheet(
            "#crackConsoleText {"
            "background-color: #050810;"
            "color: #39ff14;"
            "font-family: 'Fira Code', 'Source Code Pro', monospace;"
            "font-size: 12pt;"
            "padding: 6px;"
            "selection-background-color: #245f3e;"
            "selection-color: #e6ffe6;"
            "}"
        )

        layout.addWidget(header)
        layout.addWidget(self._text_area, stretch=1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)  # type: ignore[attr-defined]

    def _on_visual_action(self, action: VisualAction) -> None:
        self._buffer.handle_visual_action(action)
        if not self._timer.isActive():
            self._timer.start(self.TICK_INTERVAL_MS)

    def _on_tick(self) -> None:
        if not self._buffer.step():
            if self._buffer.idle:
                self._timer.stop()
            return
        self._render()

    def _render(self) -> None:
        lines = "\n".join(self._buffer.render_lines())
        self._text_area.setPlainText(lines)
        scrollbar: QScrollBar | None = self._text_area.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event: QCloseEvent) -> None:  # pragma: no cover - Qt integration
        if self._timer.isActive():
            self._timer.stop()
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        super().closeEvent(event)


class ModeStatusBar(QStatusBar):
    """Status bar tracking the current runtime mode and state chips."""

    def __init__(self, bus: EventBus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mode_label = QLabel("Mode: --")
        self.fps_label = QLabel("FPS: --")
        self.effects_label = QLabel("Effects: none")
        self.panic_button = QPushButton("PANIC")
        self.panic_button.setObjectName("panic_button")
        self.panic_button.setToolTip("Immediately stop all effects (Ctrl+.)")

        self._bus = bus
        self._indicators = StatusIndicators()
        self._unsubscribe = bus.subscribe(SystemAction, self._on_system_action)
        self.destroyed.connect(self._teardown)  # type: ignore[attr-defined]

        for widget, name in (
            (self.mode_label, "mode"),
            (self.fps_label, "fps"),
            (self.effects_label, "effects"),
        ):
            widget.setObjectName(f"status_{name}")
            self.addPermanentWidget(widget)
        self.addPermanentWidget(self.panic_button)
        self._refresh_labels()

    def update_mode(self, mode: str) -> None:
        """Update the prominent mode indicator."""

        self.mode_label.setText(f"Mode: {mode}")

    def _on_system_action(self, action: SystemAction) -> None:
        if self._indicators.handle_system_action(action):
            self._refresh_labels()

    def _refresh_labels(self) -> None:
        self.fps_label.setText(self._indicators.fps_chip())
        self.effects_label.setText(self._indicators.effects_chip())

    def _teardown(self) -> None:
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None


class MainWindow(QMainWindow):
    """Primary application window for the Chaos Keyboard UI."""

    _DEFAULT_EFFECT_BINDINGS: ClassVar[tuple[tuple[object, str], ...]] = (
        (Qt.Key_F1, "fake_bsod"),
        (Qt.Key_F2, "force_close"),
        (Qt.Key_F3, "popup_storm"),
        (Qt.Key_F4, "fake_exfil"),
        (Qt.Key_F5, "mock_keylogger"),
        (Qt.Key_F6, "key_swap"),
        (Qt.Key_F7, "invert_screen"),
        (Qt.Key_F8, "high_contrast"),
        (Qt.Key_F9, "mouse_gremlin"),
        (Qt.Key_F10, "matrix_shader"),
        (Qt.Key_F11, "fake_locker"),
        (Qt.Key_F12, "uac_mirage"),
        (Qt.Key_AsciiTilde, "terminal_storm"),
        (Qt.Key_1, "net_outage"),
        (Qt.Key_2, "disk_full"),
        (Qt.Key_3, "cpu_heater"),
        (Qt.Key_4, "lag_spike"),
        (Qt.Key_5, "typer_gremlin"),
        (Qt.Key_6, "caps_roulette"),
        (Qt.Key_7, "window_wobble"),
        (Qt.Key_8, "ascii_snow"),
        (Qt.Key_9, "fake_update"),
        (Qt.Key_0, "shame_bell"),
        ("CTRL+ALT+B", "ctrl_alt_b_briefing"),
        ("CTRL+ALT+K", "ctrl_alt_k_ethics"),
    )

    def __init__(
        self,
        mode: str = DEFAULT_MODE,
        *,
        profile: ProfileConfig | None = None,
        event_bus: EventBus | None = None,
        telemetry: TelemetryLogger | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Chaos Keyboard")
        self.resize(1024, 768)

        self._profile = self._resolve_profile(profile)
        self._mode = ensure_sim_only_mode(mode)
        self._event_bus = event_bus or EventBus()
        self._safety_context = SafetyContext(self._mode)
        self._telemetry = telemetry or TelemetryLogger(pretty_stream=sys.stdout)
        self._effects = EffectController(
            self._safety_context,
            self._event_bus,
            telemetry=self._telemetry,
        )
        self._effect_allowlist = (
            frozenset(effect.strip().lower() for effect in self._profile.effects.enabled)
            if self._profile is not None
            else None
        )
        self._skin = self._profile.ui.skin if self._profile is not None else "crt"
        self._scanlines_enabled = (
            self._profile.ui.scanlines if self._profile is not None else True
        )
        self._audio_enabled = (
            self._profile.audio.enabled if self._profile is not None else True
        )
        self._limits = self._profile.limits if self._profile is not None else None
        self._start_fullscreen = (
            self._profile.ui.fullscreen if self._profile is not None else False
        )
        self._bind_default_effects()

        central = QWidget(self)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Vertical, central)
        splitter.addWidget(KeyboardGrid(splitter))
        splitter.addWidget(CrackConsolePanel(self._event_bus, splitter))
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        central_layout.addWidget(splitter)
        self.setCentralWidget(central)

        status_bar = ModeStatusBar(self._event_bus, self)
        self.setStatusBar(status_bar)
        status_bar.update_mode(self._mode)
        status_bar.panic_button.clicked.connect(self._on_panic_button)  # type: ignore[attr-defined]

        self._apply_profile_configuration()

    def _resolve_profile(self, profile: ProfileConfig | None) -> ProfileConfig | None:
        if profile is not None:
            return profile
        try:
            return active_profile()
        except ConfigError:
            return None

    def _apply_profile_configuration(self) -> None:
        self._bind_default_effects()
        if self._profile is None:
            return
        self.setProperty("skin", self._skin)
        self.setProperty("scanlines", self._scanlines_enabled)
        audio_payload = {
            "enabled": self._audio_enabled,
            "music": self._profile.audio.music,
            "sfx": self._profile.audio.sfx,
        }
        self._event_bus.publish(SystemAction(name="audio_state", payload=audio_payload))
        self._event_bus.publish(
            SystemAction(
                name="limits_applied",
                payload={
                    "max_popups": self._limits.max_popups if self._limits else None,
                    "cpu_ms": self._limits.cpu_ms if self._limits else None,
                },
            )
        )
        self._event_bus.publish(
            VisualAction(
                target="ui_skin",
                description=(
                    f"Skin set to {self._skin} with"
                    f" scanlines={'on' if self._scanlines_enabled else 'off'}."
                ),
            )
        )
        self._event_bus.publish(
            SystemAction(name="profile_applied", payload=profile_payload(self._profile))
        )
        if self._telemetry is not None:
            self._telemetry.log(
                "profile_loaded",
                payload=profile_payload(self._profile),
            )

    @property
    def mode(self) -> str:
        """Return the current runtime mode."""

        return self._mode

    @property
    def event_bus(self) -> EventBus:
        """Expose the window's event bus for subscriber registration."""

        return self._event_bus

    def set_mode(self, mode: str) -> None:
        """Set the runtime mode and refresh the status bar."""

        self._mode = ensure_sim_only_mode(mode)
        self._effects.close()
        self._safety_context = SafetyContext(self._mode)
        self._effects = EffectController(
            self._safety_context,
            self._event_bus,
            telemetry=self._telemetry,
        )
        self._bind_default_effects()
        status = self.statusBar()
        if isinstance(status, ModeStatusBar):
            status.update_mode(self._mode)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # pragma: no cover - Qt integration
        """Publish key press events to the event bus before default handling."""

        is_panic_shortcut = bool(
            event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_Period
        )
        if self._telemetry is not None:
            payload = {
                "key": event.key(),
                "text": event.text(),
                "modifiers": int(event.modifiers()),
            }
            self._telemetry.log(
                "key_press",
                payload=payload,
                redact_fields={"text"},
            )
        if not is_panic_shortcut and self._event_bus is not None:
            action = SystemAction(
                name="key_press",
                payload={
                    "key": event.key(),
                    "text": event.text(),
                    "modifiers": int(event.modifiers()),
                },
            )
            self._event_bus.publish(action)

        if is_panic_shortcut:
            self._trigger_panic(source="shortcut")
            event.accept()
            return

        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:  # pragma: no cover - Qt integration
        """Ensure effects are stopped before closing the window."""

        self._effects.close()
        if self._telemetry is not None:
            self._telemetry.log("window_closed", payload={"mode": self._mode})
        super().closeEvent(event)

    def _on_panic_button(self) -> None:  # pragma: no cover - Qt integration
        self._trigger_panic(source="button")

    def _trigger_panic(self, *, source: str) -> None:
        """Invoke the global panic stop and log watchdog status."""

        self._safety_context.panic()
        if self._telemetry is None:
            return
        watchdog = self._safety_context.watchdog
        self._telemetry.log(
            "panic_triggered",
            payload={
                "source": source,
                "max_stop_duration": watchdog.max_stop_duration,
                "completed_within_threshold": watchdog.wait_for_panic(timeout=0.0),
            },
        )

    def _bind_default_effects(self) -> None:
        """Bind the default keyboard shortcuts to effects."""

        allowlist = self._effect_allowlist
        for key, effect_name in self._DEFAULT_EFFECT_BINDINGS:
            self._effects.unbind_key(key)
            if allowlist is not None and effect_name not in allowlist:
                continue
            self._effects.bind_key(key, effect_name)


def create_application(
    mode: str | None = None,
    event_bus: EventBus | None = None,
    *,
    profile: ProfileConfig | None = None,
    telemetry: TelemetryLogger | None = None,
) -> Tuple[QApplication, MainWindow]:
    """Create the Qt application and the main window."""

    app = QApplication.instance()
    if app is None:
        app = QApplication(["ChaosKeyboard"])

    bus = event_bus or EventBus()
    window = MainWindow(
        mode or DEFAULT_MODE,
        profile=profile,
        event_bus=bus,
        telemetry=telemetry,
    )
    return app, window


def main(mode: str | None = None, *, profile: ProfileConfig | None = None) -> int:
    """Launch the Qt application and start the event loop."""

    app, window = create_application(mode, profile=profile)
    if profile is not None and profile.ui.fullscreen:
        window.showFullScreen()
    else:
        window.show()
    return app.exec()
