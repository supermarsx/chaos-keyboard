"""Simulation-only matrix shader variant cycling effect."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, FrozenSet, Sequence

from ..bus import EventBus, VisualAction
from ..safety import SafetyContext
from . import Effect, register_effect

__all__ = ["MatrixShaderEffect"]


@dataclass
class MatrixShaderEffect:
    """Cycle through faux shader presets for the retro display."""

    context: SafetyContext
    bus: EventBus
    name: ClassVar[str] = "matrix_shader"
    capabilities: ClassVar[FrozenSet[str]] = frozenset({"overlay"})
    _active: bool = False
    _variant_index: int = 0
    _variants: Sequence[str] = (
        "rainfall",
        "crt_glitch",
        "holographic_scan",
    )

    def start(self) -> None:
        if self._active:
            return
        self._active = True
        self._variant_index = 0
        self._announce_variant("engaged")

    def stop(self) -> None:
        if not self._active:
            return
        self._active = False
        self.bus.publish(
            VisualAction(
                target="overlay",
                description="Matrix shader disabled; returning to baseline render.",
            )
        )

    def status(self) -> str:
        variant = self._variants[self._variant_index]
        state = "running" if self._active else "idle"
        return f"{state} (variant={variant})"

    def cycle(self) -> None:
        """Advance to the next shader variant while active."""

        if not self._active:
            return
        self._variant_index = (self._variant_index + 1) % len(self._variants)
        self._announce_variant("cycled")

    def _announce_variant(self, action: str) -> None:
        variant = self._variants[self._variant_index]
        self.bus.publish(
            VisualAction(
                target="overlay",
                description=f"Matrix shader {action}: {variant.replace('_', ' ')}",
            )
        )


@register_effect(MatrixShaderEffect.name, capabilities=MatrixShaderEffect.capabilities)
def _factory(context: SafetyContext, bus: EventBus) -> Effect:
    return MatrixShaderEffect(context=context, bus=bus)

