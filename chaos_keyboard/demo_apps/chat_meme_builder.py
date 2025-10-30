"""Chat meme builder demo for Chaos Keyboard."""
from __future__ import annotations

from ..logging import TelemetryLogger

try:  # pragma: no cover - import side effect
    from PySide6.QtCore import Slot
    from PySide6.QtWidgets import (
        QListWidget,
        QListWidgetItem,
        QPushButton,
        QPlainTextEdit,
        QTextBrowser,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - handled at runtime
    raise ModuleNotFoundError(
        "PySide6 must be installed to launch the chat meme builder demo."
    ) from exc


class ChatMemeBuilderWindow(QWidget):
    """Simple generator that assembles faux chat memes locally."""

    _TEMPLATES = {
        "Security Team vs. Devs": (
            "Security",
            "Did you deploy the patch?",
            "Devs",
            "Define 'deploy'...",
        ),
        "Analyst All-Hands": (
            "Analyst",
            "I'm in the logs!",
            "Manager",
            "We're presenting in 5 minutes.",
        ),
        "Retro Hacker": (
            "Hacker",
            "I rewrote the worm in BASIC",
            "Friend",
            "Please don't."
        ),
    }

    def __init__(
        self,
        telemetry: TelemetryLogger | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Chat Meme Studio (Sim)")
        self.resize(560, 400)

        self._telemetry = telemetry

        self._templates_widget = QListWidget(self)
        for template_name in self._TEMPLATES:
            QListWidgetItem(template_name, self._templates_widget)
        self._templates_widget.setCurrentRow(0)

        self._script = QPlainTextEdit(self)
        self._script.setPlaceholderText("Type your punchline or stage directions...")

        generate_button = QPushButton("Render Meme", self)
        generate_button.clicked.connect(self._on_generate_clicked)

        self._preview = QTextBrowser(self)
        self._preview.setOpenExternalLinks(False)
        self._preview.setHtml("<p><em>Select a template and craft a meme.</em></p>")

        layout = QVBoxLayout(self)
        layout.addWidget(self._templates_widget)
        layout.addWidget(self._script)
        layout.addWidget(generate_button)
        layout.addWidget(self._preview)

        if self._telemetry is not None:
            self._telemetry.log("demo_chat_opened", payload={"window": self.windowTitle()})

    @Slot()
    def _on_generate_clicked(self) -> None:
        current_item = self._templates_widget.currentItem()
        template_name = current_item.text() if current_item is not None else "Security Team vs. Devs"
        lines = self._TEMPLATES.get(template_name, ("", "", "", ""))
        script = self._script.toPlainText().strip()
        outro = script.splitlines()[0] if script else "(no custom text)"
        html = (
            f"<h3>{template_name}</h3>"
            f"<p><strong>{lines[0]}:</strong> {lines[1]}</p>"
            f"<p><strong>{lines[2]}:</strong> {lines[3]}</p>"
            f"<p><strong>You:</strong> {outro}</p>"
        )
        self._preview.setHtml(html)
        if self._telemetry is not None:
            self._telemetry.log(
                "demo_chat_render",
                payload={"template": template_name, "chars": len(script)},
            )
