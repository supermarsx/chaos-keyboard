"""Core Qt application scaffolding for Chaos Keyboard."""
from __future__ import annotations

from typing import Tuple

from . import DEFAULT_MODE, ensure_sim_only_mode

try:  # pragma: no cover - import side effect
    from PySide6.QtCore import Qt
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

    def __init__(self, mode: str = DEFAULT_MODE) -> None:
        super().__init__()
        self.setWindowTitle("Chaos Keyboard")
        self.resize(1024, 768)

        self._mode = ensure_sim_only_mode(mode)

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

    def set_mode(self, mode: str) -> None:
        """Set the runtime mode and refresh the status bar."""

        self._mode = ensure_sim_only_mode(mode)
        status = self.statusBar()
        if isinstance(status, ModeStatusBar):
            status.update_mode(self._mode)


def create_application(mode: str | None = None) -> Tuple[QApplication, MainWindow]:
    """Create the Qt application and the main window."""

    app = QApplication.instance()
    if app is None:
        app = QApplication(["ChaosKeyboard"])

    window = MainWindow(mode or DEFAULT_MODE)
    return app, window


def main(mode: str | None = None) -> int:
    """Launch the Qt application and start the event loop."""

    app, window = create_application(mode)
    window.show()
    return app.exec()
