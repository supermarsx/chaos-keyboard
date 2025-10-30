"""Retro browser simulation used by Chaos Keyboard demo effects."""
from __future__ import annotations

from ..logging import TelemetryLogger

try:  # pragma: no cover - import side effect
    from PySide6.QtCore import Slot
    from PySide6.QtWidgets import (
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QTextBrowser,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - handled at runtime
    raise ModuleNotFoundError(
        "PySide6 must be installed to launch the retro browser demo."
    ) from exc


class RetroBrowserWindow(QWidget):
    """A tiny offline browser that renders canned retro pages."""

    _PAGES = {
        "home": (
            "RETRO GRID BBS",
            "Welcome back, sysop!<br/>Select a feed from the dropdown to continue.",
        ),
        "news": (
            "BYTEBUSTER NEWS",
            "<ul><li>2024-09-01: Chaos Keyboard ships new faux exploits.</li>"
            "<li>Patch Tuesday: 47 vulnerabilities in simulated BIOS firmware.</li></ul>",
        ),
        "chat": (
            "ELITE CHAT",
            "<p><em>+Z0RK:</em> anybody got the new ANSI art pack?</p>",
        ),
        "downloads": (
            "FILE VAULT",
            "<p>All downloads disabled in SIM ONLY mode.</p>",
        ),
    }

    def __init__(
        self,
        telemetry: TelemetryLogger | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("NebulaNavigator 95 (Sim)")
        self.resize(720, 480)

        self._telemetry = telemetry

        self._address = QLineEdit(self)
        self._address.setPlaceholderText("retro://home")
        self._address.returnPressed.connect(self._on_navigate)

        go_button = QPushButton("Go", self)
        go_button.clicked.connect(self._on_navigate)

        address_layout = QHBoxLayout()
        address_layout.addWidget(QLabel("Address", self))
        address_layout.addWidget(self._address)
        address_layout.addWidget(go_button)

        self._viewer = QTextBrowser(self)
        self._viewer.setOpenExternalLinks(False)
        self._viewer.setHtml("<h2>RETRO GRID BBS</h2><p>Awaiting input...</p>")

        layout = QVBoxLayout(self)
        layout.addLayout(address_layout)
        layout.addWidget(self._viewer)

        if self._telemetry is not None:
            self._telemetry.log("demo_browser_opened", payload={"window": self.windowTitle()})

    @Slot()
    def _on_navigate(self) -> None:
        raw = self._address.text().strip() or "retro://home"
        page_key = raw.split("//")[-1].lower()
        title, body = self._PAGES.get(page_key, ("MISSING", "<p>File not found in archive.</p>"))
        self._viewer.setHtml(f"<h2>{title}</h2>{body}")
        if self._telemetry is not None:
            self._telemetry.log(
                "demo_browser_navigate",
                payload={"page": page_key, "url": raw},
                redact_fields={"url"},
            )
