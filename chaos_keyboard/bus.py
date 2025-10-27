"""Lightweight publish/subscribe event bus for Chaos Keyboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Mapping, Type, TypeVar


class _BaseAction:
    """Marker superclass for typed actions dispatched on the event bus."""


@dataclass(frozen=True)
class EffectAction(_BaseAction):
    """Describe an effect triggered by a keyboard interaction."""

    key: str
    effect: str


@dataclass(frozen=True)
class SystemAction(_BaseAction):
    """Describe a system-level action emitted by the application."""

    name: str
    payload: Mapping[str, object] | None = None


@dataclass(frozen=True)
class VisualAction(_BaseAction):
    """Describe a visual update to be rendered in the UI."""

    target: str
    description: str


ActionType = TypeVar("ActionType", bound=_BaseAction)


class EventBus:
    """Dispatch typed actions to registered subscribers."""

    def __init__(self) -> None:
        self._subscribers: Dict[Type[_BaseAction], List[Callable[[_BaseAction], None]]] = {}

    def subscribe(
        self, action_type: Type[ActionType], callback: Callable[[ActionType], None]
    ) -> Callable[[], None]:
        """Register a callback for a particular action type."""

        callbacks = self._subscribers.setdefault(action_type, [])
        callbacks.append(callback)  # type: ignore[arg-type]

        def unsubscribe() -> None:
            listeners = self._subscribers.get(action_type)
            if not listeners:
                return
            try:
                listeners.remove(callback)  # type: ignore[arg-type]
            except ValueError:
                return
            if not listeners:
                self._subscribers.pop(action_type, None)

        return unsubscribe

    def publish(self, action: ActionType) -> None:
        """Publish an action to all subscribers whose type matches."""

        for action_type, callbacks in list(self._subscribers.items()):
            if isinstance(action, action_type):
                for callback in list(callbacks):
                    callback(action)  # type: ignore[arg-type]

