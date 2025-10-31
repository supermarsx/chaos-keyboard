"""State management for the retro Crack Console widget."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable, Sequence

from .bus import VisualAction

__all__ = ["ConsoleBuffer", "ConsoleMessage"]


@dataclass(slots=True)
class ConsoleMessage:
    """Represent a single console message with incremental rendering state."""

    text: str
    rendered: str = ""

    def step(self, characters: int) -> bool:
        """Reveal up to ``characters`` additional characters.

        Returns
        -------
        bool
            ``True`` when the rendered text changed.
        """

        if self.completed:
            return False
        step = max(1, characters)
        next_length = min(len(self.text), len(self.rendered) + step)
        if next_length == len(self.rendered):
            return False
        self.rendered = self.text[:next_length]
        return True

    @property
    def completed(self) -> bool:
        """Whether the full message has been rendered."""

        return self.rendered == self.text


class ConsoleBuffer:
    """Maintain a scrollback buffer with type-out animation state."""

    def __init__(
        self,
        *,
        capacity: int = 200,
        chars_per_tick: int = 2,
    ) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if chars_per_tick <= 0:
            raise ValueError("chars_per_tick must be positive")
        self.capacity = capacity
        self.chars_per_tick = chars_per_tick
        self._history: Deque[str] = deque(maxlen=capacity)
        self._queue: Deque[ConsoleMessage] = deque()
        self._active: ConsoleMessage | None = None
        self._sequence = 0

    def handle_visual_action(self, action: VisualAction) -> None:
        """Convert a :class:`~chaos_keyboard.bus.VisualAction` into a message."""

        description = action.description.strip()
        if not description:
            return
        target = action.target.strip() or "*"
        stylised = self._stylise(target, description)
        self.enqueue(stylised)

    def enqueue(self, message: str) -> None:
        """Append a raw message string to the buffer queue."""

        clean = message.strip()
        if not clean:
            return
        console_message = ConsoleMessage(text=clean)
        if self._active is None:
            self._active = console_message
        else:
            self._queue.append(console_message)

    def step(self, *, ticks: int = 1) -> bool:
        """Advance the type-out animation by ``ticks`` timer intervals."""

        changed = False
        iterations = max(1, ticks)
        for _ in range(iterations):
            if self._active is None:
                self._advance_to_next()
                if self._active is None:
                    break
            changed |= self._active.step(self.chars_per_tick)
            if self._active.completed:
                self._commit_active()
        return changed

    def flush(self) -> None:
        """Render all queued messages immediately."""

        while not self.idle:
            if self._active is None:
                self._advance_to_next()
                continue
            self._active.rendered = self._active.text
            self._commit_active()

    @property
    def idle(self) -> bool:
        """Return ``True`` when no queued messages remain."""

        return self._active is None and not self._queue

    def render_lines(self) -> Sequence[str]:
        """Return the rendered history including the active message."""

        lines = list(self._history)
        if self._active is not None and self._active.rendered:
            lines.append(self._active.rendered)
        return tuple(lines)

    def _stylise(self, target: str, description: str) -> str:
        self._sequence = (self._sequence + 1) % 0xFFFF
        prefix = f"0x{self._sequence:04X}"
        channel = target.strip().upper().replace(" ", "_") or "*"
        payload = description.upper()
        return f"{prefix} ▸ {channel}: {payload}"

    def _advance_to_next(self) -> None:
        if self._queue:
            self._active = self._queue.popleft()
        else:
            self._active = None

    def _commit_active(self) -> None:
        if self._active is None:
            return
        self._history.append(self._active.text)
        self._advance_to_next()

    def __iter__(self) -> Iterable[str]:  # pragma: no cover - convenience
        return iter(self.render_lines())
