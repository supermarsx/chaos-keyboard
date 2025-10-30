"""Core Qt application scaffolding for Chaos Keyboard."""
from __future__ import annotations

import sys
from typing import Tuple

from . import DEFAULT_MODE, ensure_sim_only_mode
from .bus import EventBus, SystemAction
from .effects import EffectController
from .logging import TelemetryLogger
from .safety import SafetyContext

try:  # pragma: no cover - import side effect
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QCloseEvent, QKeyEvent
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QGridLayout,
        QLabel,
        QMainWindow,
        QSizePolicy,
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
    """Placeholder widget for the animated Crack Console view."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("crackConsole")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Sunken)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        header = QLabel("Crack Console")
        header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setStyleSheet("font-weight: bold; text-transform: uppercase;")

        body = QLabel(
            "Console output placeholder.\n"
            "Future versions will stream faux assembly logs and hex dumps."
        )
        body.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        body.setWordWrap(True)
        body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addWidget(header)
        layout.addWidget(body)


class ModeStatusBar(QStatusBar):
    """Status bar tracking the current runtime mode and state chips."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.mode_label = QLabel("Mode: --")
        self.fps_label = QLabel("FPS: --")
        self.effects_label = QLabel("Effects: none")

        for widget, name in (
            (self.mode_label, "mode"),
            (self.fps_label, "fps"),
            (self.effects_label, "effects"),
        ):
            widget.setObjectName(f"status_{name}")
            self.addPermanentWidget(widget)

    def update_mode(self, mode: str) -> None:
        """Update the prominent mode indicator."""

        self.mode_label.setText(f"Mode: {mode}")


class MainWindow(QMainWindow):
    """Primary application window for the Chaos Keyboard UI."""

    def __init__(
        self,
        mode: str = DEFAULT_MODE,
        event_bus: EventBus | None = None,
        telemetry: TelemetryLogger | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Chaos Keyboard")
        self.resize(1024, 768)

        self._mode = ensure_sim_only_mode(mode)
        self._event_bus = event_bus or EventBus()
        self._safety_context = SafetyContext(self._mode)
        self._telemetry = telemetry or TelemetryLogger(pretty_stream=sys.stdout)
        self._effects = EffectController(
            self._safety_context,
            self._event_bus,
            telemetry=self._telemetry,
        )
        self._bind_default_effects()

        central = QWidget(self)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Vertical, central)
        splitter.addWidget(KeyboardGrid(splitter))
        splitter.addWidget(CrackConsolePanel(splitter))
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        central_layout.addWidget(splitter)
        self.setCentralWidget(central)

        status_bar = ModeStatusBar(self)
        self.setStatusBar(status_bar)
        status_bar.update_mode(self._mode)

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
        if self._event_bus is not None:
            action = SystemAction(
                name="key_press",
                payload={
                    "key": event.key(),
                    "text": event.text(),
                    "modifiers": int(event.modifiers()),
                },
            )
            self._event_bus.publish(action)

        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:  # pragma: no cover - Qt integration
        """Ensure effects are stopped before closing the window."""

        self._effects.close()
        if self._telemetry is not None:
            self._telemetry.log("window_closed", payload={"mode": self._mode})
        super().closeEvent(event)

    def _bind_default_effects(self) -> None:
        """Bind the default keyboard shortcuts to effects."""

        self._effects.bind_key(Qt.Key_F1, "fake_bsod")
        self._effects.bind_key(Qt.Key_F3, "popup_storm")
        self._effects.bind_key(Qt.Key_F5, "mock_keylogger")
        self._effects.bind_key(Qt.Key_F6, "matrix_rain")


def create_application(
    mode: str | None = None,
    event_bus: EventBus | None = None,
    *,
    telemetry: TelemetryLogger | None = None,
) -> Tuple[QApplication, MainWindow]:
    """Create the Qt application and the main window."""

    app = QApplication.instance()
    if app is None:
        app = QApplication(["ChaosKeyboard"])

    bus = event_bus or EventBus()
    window = MainWindow(
        mode or DEFAULT_MODE,
        event_bus=bus,
        telemetry=telemetry,
    )
    return app, window


def main(mode: str | None = None) -> int:
    """Launch the Qt application and start the event loop."""

    app, window = create_application(mode)
    window.show()
    return app.exec()
