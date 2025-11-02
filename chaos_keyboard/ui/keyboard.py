"""Virtual keyboard widget rendered with pixel-art styled keycaps."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Sequence

from PySide6.QtCore import QRect, Qt, QSize
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..bus import EffectAction, EventBus, SystemAction


@dataclass(frozen=True)
class KeyPlacement:
    """Describe a single keycap within a keyboard layout."""

    identifier: str
    label: str
    row: int
    column: int
    width: int = 1
    height: int = 1
    binding: object | None = None
    qt_key: int | None = None
    text: str | None = None
    modifiers: int = 0

    def combo(self) -> str | None:
        """Return a formatted combo string when modifiers are present."""

        if not self.modifiers:
            return None
        parts: list[str] = []
        for flag, name in (
            (int(Qt.ShiftModifier), "SHIFT"),
            (int(Qt.ControlModifier), "CTRL"),
            (int(Qt.AltModifier), "ALT"),
            (int(Qt.MetaModifier), "META"),
        ):
            if self.modifiers & flag:
                parts.append(name)
        if not parts:
            return None
        key_label: str | None
        if self.text:
            key_label = self.text.upper()
        elif isinstance(self.binding, str) and "+" not in self.binding:
            key_label = self.binding.upper()
        elif self.label:
            key_label = self.label.replace("\n", " ").strip().upper()
        else:
            key_label = None
        if not key_label:
            return None
        parts.append(key_label)
        return "+".join(parts)


@dataclass(frozen=True)
class KeyboardLayout:
    """Declarative description of a keyboard layout."""

    name: str
    keys: Sequence[KeyPlacement]

    @property
    def column_count(self) -> int:
        """Return the number of columns required for the layout."""

        if not self.keys:
            return 0
        return max(key.column + key.width for key in self.keys)

    @property
    def row_count(self) -> int:
        """Return the number of rows required for the layout."""

        if not self.keys:
            return 0
        return max(key.row + key.height for key in self.keys)


class KeycapButton(QPushButton):
    """Custom button drawing a pixel-art style keycap."""

    def __init__(self, placement: KeyPlacement, parent: QWidget | None = None) -> None:
        super().__init__(placement.label, parent)
        self._placement = placement
        self.setFlat(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setObjectName(f"keycap_{placement.identifier}")
        self._base_color = QColor(26, 31, 44)
        self._border_light = QColor(120, 200, 255)
        self._border_dark = QColor(8, 12, 20)
        self._face_light = QColor(54, 68, 92)
        self._face_dark = QColor(18, 22, 34)
        self._text_color = QColor(227, 247, 255)

    @property
    def placement(self) -> KeyPlacement:
        """Return the placement metadata for the key."""

        return self._placement

    def sizeHint(self) -> QSize:  # pragma: no cover - visual sizing
        base = super().sizeHint()
        width = max(base.width(), 48) * self._placement.width
        height = max(base.height(), 48) * self._placement.height
        return QSize(width, height)

    def paintEvent(self, event: QPaintEvent) -> None:  # pragma: no cover - Qt painting
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing, False)
        rect = self.rect()

        # Outer bezel
        painter.fillRect(rect, self._border_dark)
        inner = rect.adjusted(3, 3, -3, -3)
        painter.fillRect(inner, self._base_color)

        # Keycap face with faux depth
        face = inner.adjusted(3, 3, -3, -3)
        painter.fillRect(face, self._face_dark)
        highlight = QRect(face.left(), face.top(), face.width(), 4)
        shadow = QRect(face.left(), face.bottom() - 4, face.width(), 4)
        painter.fillRect(highlight, self._face_light)
        painter.fillRect(shadow, self._border_dark)

        # Border accents
        painter.setPen(self._border_light)
        painter.drawLine(inner.left(), inner.top(), inner.right(), inner.top())
        painter.drawLine(inner.left(), inner.top(), inner.left(), inner.bottom())
        painter.setPen(self._border_dark)
        painter.drawLine(inner.left(), inner.bottom(), inner.right(), inner.bottom())
        painter.drawLine(inner.right(), inner.top(), inner.right(), inner.bottom())

        # Render key legend
        painter.setPen(self._text_color)
        lines = self.text().splitlines() or [""]
        metrics = painter.fontMetrics()
        total_height = len(lines) * metrics.height()
        top = face.top() + max((face.height() - total_height) // 2, 4)
        for index, line in enumerate(lines):
            y = top + metrics.ascent() + index * metrics.height()
            painter.drawText(face.left() + 8, y, line.upper())


class KeyboardPanel(QFrame):
    """Interactive panel rendering the virtual keyboard layout."""

    def __init__(
        self,
        bus: EventBus,
        effect_bindings: Iterable[tuple[object, str]] | Mapping[object, str],
        *,
        parent: QWidget | None = None,
        default_layout: KeyboardLayout | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("keyboardPanel")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setStyleSheet(
            "#keyboardPanel {"
            "background-color: #04070d;"
            "border: 2px solid #1c2b3f;"
            "}"
        )

        self._bus = bus
        self._effect_bindings = self._normalise_bindings(effect_bindings)
        self._layouts: Dict[str, KeyboardLayout] = {
            layout.name: layout for layout in (ANSI_LAYOUT, ISO_LAYOUT)
        }
        if default_layout is not None:
            self._layouts[default_layout.name] = default_layout
        self._keys: Dict[str, KeycapButton] = {}
        self._active_layout: KeyboardLayout | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("CHAOS KEYBOARD")
        title.setObjectName("keyboardTitle")
        title.setStyleSheet(
            "#keyboardTitle {"
            "color: #8cd7ff;"
            "font-size: 18pt;"
            "font-weight: 600;"
            "letter-spacing: 1px;"
            "}"
        )

        header.addWidget(title)
        header.addStretch(1)

        selector_label = QLabel("Layout")
        selector_label.setStyleSheet(
            "color: #7aa0c8; font-size: 10pt; font-weight: 500;"
        )
        self._layout_selector = QComboBox(self)
        self._layout_selector.addItems(sorted(self._layouts))
        self._layout_selector.setObjectName("layoutSelector")
        self._layout_selector.setStyleSheet(
            "#layoutSelector {"
            "background-color: #0d1520;"
            "color: #cde8ff;"
            "border: 1px solid #2c3f5a;"
            "padding: 4px 8px;"
            "}"
        )
        self._layout_selector.currentTextChanged.connect(self._on_layout_selected)

        header.addWidget(selector_label)
        header.addWidget(self._layout_selector)
        root.addLayout(header)

        self._key_container = QWidget(self)
        self._key_container.setObjectName("keyboardGrid")
        self._grid = QGridLayout(self._key_container)
        self._grid.setContentsMargins(6, 6, 6, 6)
        self._grid.setHorizontalSpacing(4)
        self._grid.setVerticalSpacing(4)
        root.addWidget(self._key_container, stretch=1)

        initial_layout = default_layout or ANSI_LAYOUT
        self.set_active_layout(initial_layout.name)

    @property
    def active_layout(self) -> KeyboardLayout:
        """Return the currently selected layout."""

        if self._active_layout is None:
            raise RuntimeError("Keyboard layout has not been initialised")
        return self._active_layout

    def set_active_layout(self, name: str) -> None:
        """Switch to the layout identified by ``name``."""

        try:
            layout = self._layouts[name]
        except KeyError as exc:
            raise KeyError(f"Unknown keyboard layout '{name}'") from exc
        if self._active_layout is layout:
            return
        self._apply_layout(layout)
        self._layout_selector.blockSignals(True)
        self._layout_selector.setCurrentText(layout.name)
        self._layout_selector.blockSignals(False)
        self._publish_layout(layout)

    def press_key(self, identifier: str) -> None:
        """Programmatically trigger the key identified by ``identifier``."""

        button = self._keys.get(identifier)
        if button is None:
            raise KeyError(f"Unknown key identifier '{identifier}'")
        button.click()

    def _apply_layout(self, layout: KeyboardLayout) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
        self._keys.clear()
        for column in range(layout.column_count):
            self._grid.setColumnStretch(column, 1)
        for row in range(layout.row_count):
            self._grid.setRowStretch(row, 1)
        for placement in layout.keys:
            button = KeycapButton(placement, self._key_container)
            button.clicked.connect(self._make_key_handler(placement))  # type: ignore[arg-type]
            self._grid.addWidget(
                button,
                placement.row,
                placement.column,
                placement.height,
                placement.width,
            )
            self._keys[placement.identifier] = button
        self._active_layout = layout

    def _make_key_handler(self, placement: KeyPlacement):
        def handler() -> None:
            self._handle_key_press(placement)

        return handler

    def _handle_key_press(self, placement: KeyPlacement) -> None:
        payload: Dict[str, object] = {}
        combo = placement.combo()
        if combo is not None:
            payload["combo"] = combo
        if placement.modifiers:
            payload["modifiers"] = placement.modifiers
        if placement.qt_key is not None:
            payload["key"] = placement.qt_key
        if placement.text is not None:
            payload["text"] = placement.text
        if payload:
            self._bus.publish(SystemAction(name="key_press", payload=payload))
        effect = self._resolve_effect(placement)
        if effect is not None:
            self._bus.publish(
                EffectAction(key=placement.identifier, effect=effect)
            )

    def _resolve_effect(self, placement: KeyPlacement) -> str | None:
        if placement.binding is not None:
            normalised = self._normalise_key(placement.binding)
            effect = self._effect_bindings.get(normalised)
            if effect is not None:
                return effect
        combo = placement.combo()
        if combo is not None:
            effect = self._effect_bindings.get(combo)
            if effect is not None:
                return effect
        if placement.qt_key is not None:
            effect = self._effect_bindings.get(self._normalise_key(placement.qt_key))
            if effect is not None:
                return effect
        if placement.text is not None:
            effect = self._effect_bindings.get(self._normalise_key(placement.text))
            if effect is not None:
                return effect
        return None

    def _publish_layout(self, layout: KeyboardLayout) -> None:
        self._bus.publish(
            SystemAction(name="keyboard_layout", payload={"layout": layout.name})
        )

    def _on_layout_selected(self, name: str) -> None:
        self.set_active_layout(name)

    @staticmethod
    def _normalise_bindings(
        bindings: Iterable[tuple[object, str]] | Mapping[object, str]
    ) -> Dict[str, str]:
        if isinstance(bindings, Mapping):
            items = bindings.items()
        else:
            items = bindings
        return {
            KeyboardPanel._normalise_key(key): value.strip().lower()
            for key, value in items
        }

    @staticmethod
    def _normalise_key(key: object) -> str:
        if isinstance(key, str):
            return key.strip().upper()
        try:
            numeric = int(key)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return str(key)
        return str(numeric)


def _build_ansi_layout() -> Sequence[KeyPlacement]:
    keys: list[KeyPlacement] = []

    # Row 0 - Escape and function keys
    keys.extend(
        (
            KeyPlacement("ESC", "ESC", 0, 0, width=2),
            KeyPlacement(
                "F1",
                "F1",
                0,
                3,
                width=2,
                binding=Qt.Key_F1,
                qt_key=Qt.Key_F1,
            ),
            KeyPlacement(
                "F2",
                "F2",
                0,
                5,
                width=2,
                binding=Qt.Key_F2,
                qt_key=Qt.Key_F2,
            ),
            KeyPlacement(
                "F3",
                "F3",
                0,
                7,
                width=2,
                binding=Qt.Key_F3,
                qt_key=Qt.Key_F3,
            ),
            KeyPlacement(
                "F4",
                "F4",
                0,
                9,
                width=2,
                binding=Qt.Key_F4,
                qt_key=Qt.Key_F4,
            ),
            KeyPlacement(
                "F5",
                "F5",
                0,
                12,
                width=2,
                binding=Qt.Key_F5,
                qt_key=Qt.Key_F5,
            ),
            KeyPlacement(
                "F6",
                "F6",
                0,
                14,
                width=2,
                binding=Qt.Key_F6,
                qt_key=Qt.Key_F6,
            ),
            KeyPlacement(
                "F7",
                "F7",
                0,
                16,
                width=2,
                binding=Qt.Key_F7,
                qt_key=Qt.Key_F7,
            ),
            KeyPlacement(
                "F8",
                "F8",
                0,
                18,
                width=2,
                binding=Qt.Key_F8,
                qt_key=Qt.Key_F8,
            ),
            KeyPlacement(
                "F9",
                "F9",
                0,
                21,
                width=2,
                binding=Qt.Key_F9,
                qt_key=Qt.Key_F9,
            ),
            KeyPlacement(
                "F10",
                "F10",
                0,
                23,
                width=2,
                binding=Qt.Key_F10,
                qt_key=Qt.Key_F10,
            ),
            KeyPlacement(
                "F11",
                "F11",
                0,
                25,
                width=2,
                binding=Qt.Key_F11,
                qt_key=Qt.Key_F11,
            ),
            KeyPlacement(
                "F12",
                "F12",
                0,
                27,
                width=2,
                binding=Qt.Key_F12,
                qt_key=Qt.Key_F12,
            ),
        )
    )

    # Row 1 - Number row
    keys.extend(
        (
            KeyPlacement(
                "BACKQUOTE",
                "~",
                1,
                0,
                width=2,
                binding=Qt.Key_AsciiTilde,
                qt_key=Qt.Key_AsciiTilde,
                text="~",
            ),
            KeyPlacement(
                "KEY_1",
                "1",
                1,
                2,
                width=2,
                binding=Qt.Key_1,
                qt_key=Qt.Key_1,
                text="1",
            ),
            KeyPlacement(
                "KEY_2",
                "2",
                1,
                4,
                width=2,
                binding=Qt.Key_2,
                qt_key=Qt.Key_2,
                text="2",
            ),
            KeyPlacement(
                "KEY_3",
                "3",
                1,
                6,
                width=2,
                binding=Qt.Key_3,
                qt_key=Qt.Key_3,
                text="3",
            ),
            KeyPlacement(
                "KEY_4",
                "4",
                1,
                8,
                width=2,
                binding=Qt.Key_4,
                qt_key=Qt.Key_4,
                text="4",
            ),
            KeyPlacement(
                "KEY_5",
                "5",
                1,
                10,
                width=2,
                binding=Qt.Key_5,
                qt_key=Qt.Key_5,
                text="5",
            ),
            KeyPlacement(
                "KEY_6",
                "6",
                1,
                12,
                width=2,
                binding=Qt.Key_6,
                qt_key=Qt.Key_6,
                text="6",
            ),
            KeyPlacement(
                "KEY_7",
                "7",
                1,
                14,
                width=2,
                binding=Qt.Key_7,
                qt_key=Qt.Key_7,
                text="7",
            ),
            KeyPlacement(
                "KEY_8",
                "8",
                1,
                16,
                width=2,
                binding=Qt.Key_8,
                qt_key=Qt.Key_8,
                text="8",
            ),
            KeyPlacement(
                "KEY_9",
                "9",
                1,
                18,
                width=2,
                binding=Qt.Key_9,
                qt_key=Qt.Key_9,
                text="9",
            ),
            KeyPlacement(
                "KEY_0",
                "0",
                1,
                20,
                width=2,
                binding=Qt.Key_0,
                qt_key=Qt.Key_0,
                text="0",
            ),
            KeyPlacement("MINUS", "-", 1, 22, width=2, text="-"),
            KeyPlacement("EQUALS", "=", 1, 24, width=2, text="="),
            KeyPlacement("BACKSPACE", "BACK", 1, 26, width=4),
        )
    )

    # Row 2 - Q row
    keys.extend(
        (
            KeyPlacement("TAB", "TAB", 2, 0, width=3),
            KeyPlacement("KEY_Q", "Q", 2, 3, width=2, text="q"),
            KeyPlacement("KEY_W", "W", 2, 5, width=2, text="w"),
            KeyPlacement("KEY_E", "E", 2, 7, width=2, text="e"),
            KeyPlacement("KEY_R", "R", 2, 9, width=2, text="r"),
            KeyPlacement("KEY_T", "T", 2, 11, width=2, text="t"),
            KeyPlacement("KEY_Y", "Y", 2, 13, width=2, text="y"),
            KeyPlacement("KEY_U", "U", 2, 15, width=2, text="u"),
            KeyPlacement("KEY_I", "I", 2, 17, width=2, text="i"),
            KeyPlacement("KEY_O", "O", 2, 19, width=2, text="o"),
            KeyPlacement("KEY_P", "P", 2, 21, width=2, text="p"),
            KeyPlacement("LBRACKET", "[", 2, 23, width=2, text="["),
            KeyPlacement("RBRACKET", "]", 2, 25, width=2, text="]"),
            KeyPlacement("BACKSLASH", "\\", 2, 27, width=3, text="\\"),
        )
    )

    # Row 3 - A row
    keys.extend(
        (
            KeyPlacement("CAPS", "CAPS", 3, 0, width=3),
            KeyPlacement("KEY_A", "A", 3, 3, width=2, text="a"),
            KeyPlacement("KEY_S", "S", 3, 5, width=2, text="s"),
            KeyPlacement("KEY_D", "D", 3, 7, width=2, text="d"),
            KeyPlacement("KEY_F", "F", 3, 9, width=2, text="f"),
            KeyPlacement("KEY_G", "G", 3, 11, width=2, text="g"),
            KeyPlacement("KEY_H", "H", 3, 13, width=2, text="h"),
            KeyPlacement("KEY_J", "J", 3, 15, width=2, text="j"),
            KeyPlacement("KEY_K", "K", 3, 17, width=2, text="k"),
            KeyPlacement("KEY_L", "L", 3, 19, width=2, text="l"),
            KeyPlacement("SEMICOLON", ";", 3, 21, width=2, text=";"),
            KeyPlacement("APOSTROPHE", "'", 3, 23, width=2, text="'"),
            KeyPlacement("ENTER", "ENTER", 3, 25, width=5),
        )
    )

    # Row 4 - Z row
    keys.extend(
        (
            KeyPlacement("SHIFT_L", "SHIFT", 4, 0, width=4),
            KeyPlacement("KEY_Z", "Z", 4, 4, width=2, text="z"),
            KeyPlacement("KEY_X", "X", 4, 6, width=2, text="x"),
            KeyPlacement("KEY_C", "C", 4, 8, width=2, text="c"),
            KeyPlacement("KEY_V", "V", 4, 10, width=2, text="v"),
            KeyPlacement("KEY_B", "B", 4, 12, width=2, text="b"),
            KeyPlacement("KEY_N", "N", 4, 14, width=2, text="n"),
            KeyPlacement("KEY_M", "M", 4, 16, width=2, text="m"),
            KeyPlacement("COMMA", ",", 4, 18, width=2, text=","),
            KeyPlacement("PERIOD", ".", 4, 20, width=2, text="."),
            KeyPlacement("SLASH", "/", 4, 22, width=2, text="/"),
            KeyPlacement("SHIFT_R", "SHIFT", 4, 24, width=6),
        )
    )

    # Row 5 - Space row
    ctrl_alt = int(Qt.ControlModifier | Qt.AltModifier)
    keys.extend(
        (
            KeyPlacement("CTRL_L", "CTRL", 5, 0, width=3),
            KeyPlacement("SUPER_L", "META", 5, 3, width=2),
            KeyPlacement("ALT_L", "ALT", 5, 5, width=2),
            KeyPlacement("SPACE", "", 5, 7, width=10, text=" "),
            KeyPlacement("ALT_R", "ALT", 5, 17, width=2),
            KeyPlacement("MENU", "MENU", 5, 19, width=2),
            KeyPlacement("CTRL_R", "CTRL", 5, 21, width=3),
            KeyPlacement(
                "CTRL_ALT_B",
                "CTRL\nALT\nB",
                5,
                24,
                width=3,
                binding="CTRL+ALT+B",
                qt_key=Qt.Key_B,
                text="b",
                modifiers=ctrl_alt,
            ),
            KeyPlacement(
                "CTRL_ALT_K",
                "CTRL\nALT\nK",
                5,
                27,
                width=3,
                binding="CTRL+ALT+K",
                qt_key=Qt.Key_K,
                text="k",
                modifiers=ctrl_alt,
            ),
        )
    )

    return tuple(keys)


def _build_iso_layout() -> Sequence[KeyPlacement]:
    keys: list[KeyPlacement] = []

    # Row 0 - Escape and function keys mirror ANSI layout
    keys.extend(
        (
            KeyPlacement("ESC", "ESC", 0, 0, width=2),
            KeyPlacement(
                "F1",
                "F1",
                0,
                3,
                width=2,
                binding=Qt.Key_F1,
                qt_key=Qt.Key_F1,
            ),
            KeyPlacement(
                "F2",
                "F2",
                0,
                5,
                width=2,
                binding=Qt.Key_F2,
                qt_key=Qt.Key_F2,
            ),
            KeyPlacement(
                "F3",
                "F3",
                0,
                7,
                width=2,
                binding=Qt.Key_F3,
                qt_key=Qt.Key_F3,
            ),
            KeyPlacement(
                "F4",
                "F4",
                0,
                9,
                width=2,
                binding=Qt.Key_F4,
                qt_key=Qt.Key_F4,
            ),
            KeyPlacement(
                "F5",
                "F5",
                0,
                12,
                width=2,
                binding=Qt.Key_F5,
                qt_key=Qt.Key_F5,
            ),
            KeyPlacement(
                "F6",
                "F6",
                0,
                14,
                width=2,
                binding=Qt.Key_F6,
                qt_key=Qt.Key_F6,
            ),
            KeyPlacement(
                "F7",
                "F7",
                0,
                16,
                width=2,
                binding=Qt.Key_F7,
                qt_key=Qt.Key_F7,
            ),
            KeyPlacement(
                "F8",
                "F8",
                0,
                18,
                width=2,
                binding=Qt.Key_F8,
                qt_key=Qt.Key_F8,
            ),
            KeyPlacement(
                "F9",
                "F9",
                0,
                21,
                width=2,
                binding=Qt.Key_F9,
                qt_key=Qt.Key_F9,
            ),
            KeyPlacement(
                "F10",
                "F10",
                0,
                23,
                width=2,
                binding=Qt.Key_F10,
                qt_key=Qt.Key_F10,
            ),
            KeyPlacement(
                "F11",
                "F11",
                0,
                25,
                width=2,
                binding=Qt.Key_F11,
                qt_key=Qt.Key_F11,
            ),
            KeyPlacement(
                "F12",
                "F12",
                0,
                27,
                width=2,
                binding=Qt.Key_F12,
                qt_key=Qt.Key_F12,
            ),
        )
    )

    # Row 1 - Number row identical to ANSI
    keys.extend(
        (
            KeyPlacement(
                "BACKQUOTE",
                "~",
                1,
                0,
                width=2,
                binding=Qt.Key_AsciiTilde,
                qt_key=Qt.Key_AsciiTilde,
                text="~",
            ),
            KeyPlacement(
                "KEY_1",
                "1",
                1,
                2,
                width=2,
                binding=Qt.Key_1,
                qt_key=Qt.Key_1,
                text="1",
            ),
            KeyPlacement(
                "KEY_2",
                "2",
                1,
                4,
                width=2,
                binding=Qt.Key_2,
                qt_key=Qt.Key_2,
                text="2",
            ),
            KeyPlacement(
                "KEY_3",
                "3",
                1,
                6,
                width=2,
                binding=Qt.Key_3,
                qt_key=Qt.Key_3,
                text="3",
            ),
            KeyPlacement(
                "KEY_4",
                "4",
                1,
                8,
                width=2,
                binding=Qt.Key_4,
                qt_key=Qt.Key_4,
                text="4",
            ),
            KeyPlacement(
                "KEY_5",
                "5",
                1,
                10,
                width=2,
                binding=Qt.Key_5,
                qt_key=Qt.Key_5,
                text="5",
            ),
            KeyPlacement(
                "KEY_6",
                "6",
                1,
                12,
                width=2,
                binding=Qt.Key_6,
                qt_key=Qt.Key_6,
                text="6",
            ),
            KeyPlacement(
                "KEY_7",
                "7",
                1,
                14,
                width=2,
                binding=Qt.Key_7,
                qt_key=Qt.Key_7,
                text="7",
            ),
            KeyPlacement(
                "KEY_8",
                "8",
                1,
                16,
                width=2,
                binding=Qt.Key_8,
                qt_key=Qt.Key_8,
                text="8",
            ),
            KeyPlacement(
                "KEY_9",
                "9",
                1,
                18,
                width=2,
                binding=Qt.Key_9,
                qt_key=Qt.Key_9,
                text="9",
            ),
            KeyPlacement(
                "KEY_0",
                "0",
                1,
                20,
                width=2,
                binding=Qt.Key_0,
                qt_key=Qt.Key_0,
                text="0",
            ),
            KeyPlacement("MINUS", "-", 1, 22, width=2, text="-"),
            KeyPlacement("EQUALS", "=", 1, 24, width=2, text="="),
            KeyPlacement("BACKSPACE", "BACK", 1, 26, width=4),
        )
    )

    # Row 2 - Q row with ISO return placement
    keys.extend(
        (
            KeyPlacement("TAB", "TAB", 2, 0, width=3),
            KeyPlacement("KEY_Q", "Q", 2, 3, width=2, text="q"),
            KeyPlacement("KEY_W", "W", 2, 5, width=2, text="w"),
            KeyPlacement("KEY_E", "E", 2, 7, width=2, text="e"),
            KeyPlacement("KEY_R", "R", 2, 9, width=2, text="r"),
            KeyPlacement("KEY_T", "T", 2, 11, width=2, text="t"),
            KeyPlacement("KEY_Y", "Y", 2, 13, width=2, text="y"),
            KeyPlacement("KEY_U", "U", 2, 15, width=2, text="u"),
            KeyPlacement("KEY_I", "I", 2, 17, width=2, text="i"),
            KeyPlacement("KEY_O", "O", 2, 19, width=2, text="o"),
            KeyPlacement("KEY_P", "P", 2, 21, width=2, text="p"),
            KeyPlacement("LBRACKET", "[", 2, 23, width=2, text="["),
            KeyPlacement("RBRACKET", "]", 2, 25, width=2, text="]"),
            KeyPlacement("ENTER", "ENTER", 2, 27, width=4, height=2),
        )
    )

    # Row 3 - A row with tall ISO return
    keys.extend(
        (
            KeyPlacement("CAPS", "CAPS", 3, 0, width=3),
            KeyPlacement("KEY_A", "A", 3, 3, width=2, text="a"),
            KeyPlacement("KEY_S", "S", 3, 5, width=2, text="s"),
            KeyPlacement("KEY_D", "D", 3, 7, width=2, text="d"),
            KeyPlacement("KEY_F", "F", 3, 9, width=2, text="f"),
            KeyPlacement("KEY_G", "G", 3, 11, width=2, text="g"),
            KeyPlacement("KEY_H", "H", 3, 13, width=2, text="h"),
            KeyPlacement("KEY_J", "J", 3, 15, width=2, text="j"),
            KeyPlacement("KEY_K", "K", 3, 17, width=2, text="k"),
            KeyPlacement("KEY_L", "L", 3, 19, width=2, text="l"),
            KeyPlacement("SEMICOLON", ";", 3, 21, width=2, text=";"),
            KeyPlacement("APOSTROPHE", "'", 3, 23, width=2, text="'"),
            KeyPlacement("ISO_HASH", "#", 3, 25, width=2, text="#"),
        )
    )

    # Row 4 - Z row with ISO angle bracket key
    keys.extend(
        (
            KeyPlacement("SHIFT_L", "SHIFT", 4, 0, width=3),
            KeyPlacement("ISO_LT_GT", "<\n>", 4, 3, width=2, text="<"),
            KeyPlacement("KEY_Z", "Z", 4, 5, width=2, text="z"),
            KeyPlacement("KEY_X", "X", 4, 7, width=2, text="x"),
            KeyPlacement("KEY_C", "C", 4, 9, width=2, text="c"),
            KeyPlacement("KEY_V", "V", 4, 11, width=2, text="v"),
            KeyPlacement("KEY_B", "B", 4, 13, width=2, text="b"),
            KeyPlacement("KEY_N", "N", 4, 15, width=2, text="n"),
            KeyPlacement("KEY_M", "M", 4, 17, width=2, text="m"),
            KeyPlacement("COMMA", ",", 4, 19, width=2, text=","),
            KeyPlacement("PERIOD", ".", 4, 21, width=2, text="."),
            KeyPlacement("SLASH", "/", 4, 23, width=2, text="/"),
            KeyPlacement("SHIFT_R", "SHIFT", 4, 25, width=6),
        )
    )

    # Row 5 - Space row identical to ANSI
    ctrl_alt = int(Qt.ControlModifier | Qt.AltModifier)
    keys.extend(
        (
            KeyPlacement("CTRL_L", "CTRL", 5, 0, width=3),
            KeyPlacement("SUPER_L", "META", 5, 3, width=2),
            KeyPlacement("ALT_L", "ALT", 5, 5, width=2),
            KeyPlacement("SPACE", "", 5, 7, width=10, text=" "),
            KeyPlacement("ALT_R", "ALT", 5, 17, width=2),
            KeyPlacement("MENU", "MENU", 5, 19, width=2),
            KeyPlacement("CTRL_R", "CTRL", 5, 21, width=3),
            KeyPlacement(
                "CTRL_ALT_B",
                "CTRL\nALT\nB",
                5,
                24,
                width=3,
                binding="CTRL+ALT+B",
                qt_key=Qt.Key_B,
                text="b",
                modifiers=ctrl_alt,
            ),
            KeyPlacement(
                "CTRL_ALT_K",
                "CTRL\nALT\nK",
                5,
                27,
                width=3,
                binding="CTRL+ALT+K",
                qt_key=Qt.Key_K,
                text="k",
                modifiers=ctrl_alt,
            ),
        )
    )

    return tuple(keys)


ANSI_LAYOUT = KeyboardLayout(name="ANSI", keys=_build_ansi_layout())
ISO_LAYOUT = KeyboardLayout(name="ISO", keys=_build_iso_layout())
