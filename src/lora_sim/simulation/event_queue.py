from __future__ import annotations

from dataclasses import dataclass, field
import heapq
from typing import Any


@dataclass(order=True)
class ScheduledEvent:
    event_time: float
    priority: int
    event_type: str = field(compare=False)
    payload: Any = field(compare=False)


class EventQueue:
    def __init__(self) -> None:
        self._items: list[ScheduledEvent] = []

    def push(self, event: ScheduledEvent) -> None:
        heapq.heappush(self._items, event)

    def pop(self) -> ScheduledEvent:
        return heapq.heappop(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)
