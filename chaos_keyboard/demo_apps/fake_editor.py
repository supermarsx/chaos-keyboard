"""Retro-styled fake editor sandboxed to the Chaos Keyboard process."""
from __future__ import annotations

from ..logging import TelemetryLogger

try:  # pragma: no cover - import side effect
    from PySide6.QtCore import Slot
    from PySide6.QtWidgets import (
        QLabel,
        QPushButton,
        QPlainTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - handled at runtime
    raise ModuleNotFoundError(
        "PySide6 must be installed to launch the demo editor."
    ) from exc


class FakeEditorWindow(QWidget):
    """Standalone editor that simulates typing and saving documents."""

    def __init__(
        self,
        telemetry: TelemetryLogger | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("OblivionEdit 2.0 (Sim)")
        self.resize(640, 480)

        self._telemetry = telemetry
        self._status_label = QLabel("Unsaved draft")
        self._status_label.setObjectName("status")

        self._editor = QPlainTextEdit(self)
        self._editor.setPlaceholderText("// Type your cursed macro script here...")
        self._editor.textChanged.connect(self._on_text_changed)

        save_button = QPushButton("Save (Simulated)", self)
        save_button.clicked.connect(self._on_save_clicked)

        layout = QVBoxLayout(self)
        layout.addWidget(self._status_label)
        layout.addWidget(self._editor)
        layout.addWidget(save_button)

        if self._telemetry is not None:
            self._telemetry.log("demo_editor_opened", payload={"window": self.windowTitle()})

    def capture_text(self) -> str:
        """Return the raw text currently stored in the editor."""

        return self._editor.toPlainText()

    @Slot()
    def _on_text_changed(self) -> None:
        length = len(self._editor.toPlainText())
        self._status_label.setText(f"Characters: {length}")
        if self._telemetry is not None:
            self._telemetry.log("demo_editor_changed", payload={"length": length})

    @Slot()
    def _on_save_clicked(self) -> None:
        self._status_label.setText("Saved to nowhere (simulated)")
        if self._telemetry is not None:
            self._telemetry.log("demo_editor_saved", payload={"length": len(self.capture_text())})
