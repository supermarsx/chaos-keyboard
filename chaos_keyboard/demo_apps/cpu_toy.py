"""A faux CPU load visualiser confined to the application process."""
from __future__ import annotations

from random import random

from ..logging import TelemetryLogger

try:  # pragma: no cover - import side effect
    from PySide6.QtCore import Qt, QTimer, Slot
    from PySide6.QtWidgets import QLabel, QProgressBar, QSlider, QVBoxLayout, QWidget
except ModuleNotFoundError as exc:  # pragma: no cover - handled at runtime
    raise ModuleNotFoundError(
        "PySide6 must be installed to launch the CPU toy demo."
    ) from exc


class CpuToyWindow(QWidget):
    """Widget that simulates CPU load without touching real system metrics."""

    def __init__(
        self,
        telemetry: TelemetryLogger | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Quantum 8086 Load Monitor (Sim)")
        self.resize(420, 260)

        self._telemetry = telemetry
        self._target_load = 0

        self._label = QLabel("Load target: 0%", self)
        self._progress = QProgressBar(self)
        self._progress.setRange(0, 100)

        self._slider = QSlider(Qt.Horizontal, self)
        self._slider.setRange(0, 100)
        self._slider.valueChanged.connect(self._on_slider_changed)

        layout = QVBoxLayout(self)
        layout.addWidget(self._label)
        layout.addWidget(self._progress)
        layout.addWidget(self._slider)

        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._on_timer_tick)
        self._timer.start()

        if self._telemetry is not None:
            self._telemetry.log("demo_cpu_opened", payload={"window": self.windowTitle()})

    @Slot(int)
    def _on_slider_changed(self, value: int) -> None:
        self._target_load = int(value)
        self._label.setText(f"Load target: {self._target_load}%")
        if self._telemetry is not None:
            self._telemetry.log("demo_cpu_target", payload={"target": self._target_load})

    @Slot()
    def _on_timer_tick(self) -> None:
        current = self._progress.value()
        delta = self._target_load - current
        if abs(delta) < 2:
            jitter = int(random() * 3) - 1
            self._progress.setValue(max(0, min(100, self._target_load + jitter)))
            return
        step = 5 if delta > 0 else -5
        self._progress.setValue(max(0, min(100, current + step)))
