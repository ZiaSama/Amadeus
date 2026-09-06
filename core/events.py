"""Local event delivery. No character or UI decisions belong here."""
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Event:
    kind: str
    timestamp: float  # Monotonic seconds, never persisted as a wall-clock time.
    source: str = "ui"


class EventBus:
    def __init__(self):
        self._listeners: dict[str, list[Callable[[Event], None]]] = defaultdict(list)

    def subscribe(self, kind: str, callback: Callable[[Event], None]) -> None:
        self._listeners[kind].append(callback)

    def emit(self, event: Event) -> None:
        for callback in tuple(self._listeners[event.kind]):
            callback(event)
