"""Skin manager applying themed palettes and shader presets."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QWidget

from ..assets import resolve_asset

__all__ = ["ShaderPreset", "SkinDefinition", "SkinManager"]


@dataclass(frozen=True)
class ShaderPreset:
    """Describe a fragment shader preset bundled with the UI skin."""

    identifier: str
    fragment_source: str
    uniforms: Mapping[str, float]

    def payload(self) -> dict[str, object]:
        """Return a serialisable payload describing the preset."""

        return {
            "name": self.identifier,
            "fragment": self.fragment_source,
            "uniforms": dict(self.uniforms),
        }


@dataclass(frozen=True)
class SkinDefinition:
    """Static description of an available UI skin."""

    identifier: str
    title: str
    palette: Mapping[QPalette.ColorRole, QColor]
    base_stylesheet: str
    scanline_stylesheet: str | None
    shader: ShaderPreset

    def stylesheet(self, *, scanlines: bool) -> str:
        """Return the stylesheet for the skin with optional scanlines."""

        sections: list[str] = [self.base_stylesheet.strip()]
        if scanlines and self.scanline_stylesheet:
            sections.append(self.scanline_stylesheet.strip())
        return "\n\n".join(section for section in sections if section)


class SkinManager:
    """Load bundled skins and apply them to Qt widgets."""

    def __init__(self, *, shader_root: Path | None = None) -> None:
        self._shader_root = shader_root or resolve_asset("shaders")
        self._skins = self._load_skins()

    def _load_skins(self) -> dict[str, SkinDefinition]:
        shaders = {
            "crt": self._load_shader(
                identifier="crt",
                filename="crt_scanline.frag",
                uniforms={"scanline_intensity": 0.45, "vignette_strength": 0.12},
            ),
            "dmg_boy": self._load_shader(
                identifier="dmg_boy",
                filename="dmg_boy.frag",
                uniforms={"green_tint": 0.85, "pixel_mix": 0.5},
            ),
            "trs_vibe": self._load_shader(
                identifier="trs_vibe",
                filename="trs_vibe.frag",
                uniforms={"amber_curve": 0.9, "glow_strength": 0.22},
            ),
        }

        scanline_overlay = (
            "QMainWindow#chaosMainWindow::pane {"
            "background-image: repeating-linear-gradient("
            "to bottom, rgba(0, 0, 0, 0.25) 0px, rgba(0, 0, 0, 0.25) 1px,"
            "rgba(0, 0, 0, 0.05) 1px, rgba(0, 0, 0, 0.05) 3px);"
            "background-blend-mode: multiply;"
            "}"
        )

        return {
            "crt": SkinDefinition(
                identifier="crt",
                title="CRT Overdrive",
                palette={
                    QPalette.Window: QColor(5, 9, 15),
                    QPalette.WindowText: QColor(177, 240, 255),
                    QPalette.Base: QColor(4, 7, 13),
                    QPalette.AlternateBase: QColor(9, 14, 21),
                    QPalette.Highlight: QColor(0, 180, 255),
                    QPalette.HighlightedText: QColor(6, 9, 15),
                },
                base_stylesheet=(
                    "QMainWindow#chaosMainWindow {"
                    "background-color: #05090f;"
                    "color: #b1f0ff;"
                    "font-family: 'Fira Code', 'Source Code Pro', monospace;"
                    "}"
                ),
                scanline_stylesheet=scanline_overlay,
                shader=shaders["crt"],
            ),
            "dmg_boy": SkinDefinition(
                identifier="dmg_boy",
                title="DMG-Boy Mono",
                palette={
                    QPalette.Window: QColor(208, 220, 175),
                    QPalette.WindowText: QColor(22, 51, 34),
                    QPalette.Base: QColor(195, 207, 165),
                    QPalette.AlternateBase: QColor(182, 198, 152),
                    QPalette.Highlight: QColor(80, 107, 62),
                    QPalette.HighlightedText: QColor(221, 235, 193),
                },
                base_stylesheet=(
                    "QMainWindow#chaosMainWindow {"
                    "background-color: #d0dcae;"
                    "color: #163322;"
                    "font-family: 'DM Sans', 'Fira Code', monospace;"
                    "}"
                ),
                scanline_stylesheet=None,
                shader=shaders["dmg_boy"],
            ),
            "trs_vibe": SkinDefinition(
                identifier="trs_vibe",
                title="TRS-Vibe Amber",
                palette={
                    QPalette.Window: QColor(22, 12, 4),
                    QPalette.WindowText: QColor(255, 189, 73),
                    QPalette.Base: QColor(28, 16, 6),
                    QPalette.AlternateBase: QColor(36, 20, 8),
                    QPalette.Highlight: QColor(255, 145, 0),
                    QPalette.HighlightedText: QColor(26, 14, 4),
                },
                base_stylesheet=(
                    "QMainWindow#chaosMainWindow {"
                    "background-color: #160c04;"
                    "color: #ffbd49;"
                    "font-family: 'Courier New', monospace;"
                    "letter-spacing: 1px;"
                    "}"
                ),
                scanline_stylesheet=scanline_overlay,
                shader=shaders["trs_vibe"],
            ),
        }

    def _load_shader(
        self,
        *,
        identifier: str,
        filename: str,
        uniforms: Mapping[str, float],
    ) -> ShaderPreset:
        path = self._shader_root / filename
        try:
            source = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            source = "// missing shader asset: " + filename
        return ShaderPreset(identifier=identifier, fragment_source=source, uniforms=uniforms)

    def available_skins(self) -> tuple[str, ...]:
        """Return the identifiers of all known skins."""

        return tuple(sorted(self._skins.keys()))

    def skin_for(self, name: str) -> SkinDefinition:
        """Return the skin definition for the requested name."""

        key = name.strip().lower().replace("-", "_")
        return self._skins.get(key, self._skins["crt"])

    def apply_skin(
        self,
        widget: QWidget,
        name: str,
        *,
        scanlines: bool,
    ) -> SkinDefinition:
        """Apply the named skin to a widget and return the definition."""

        skin = self.skin_for(name)
        palette = widget.palette()
        for role, color in skin.palette.items():
            palette.setColor(role, color)
        widget.setPalette(palette)
        widget.setAutoFillBackground(True)
        widget.setStyleSheet(skin.stylesheet(scanlines=scanlines))
        widget.setProperty("skin", skin.identifier)
        widget.setProperty("scanlines", bool(scanlines))
        widget.setProperty("skinShader", skin.shader.payload())
        palette_payload: dict[str, str] = {}
        for role, color in skin.palette.items():
            role_name = getattr(role, "name", None)
            if not role_name:
                role_name = str(int(role))
            palette_payload[role_name] = color.name()
        widget.setProperty("skinPalette", palette_payload)
        return skin
