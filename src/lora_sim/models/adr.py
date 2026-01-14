from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class AdrController:
    minimum_sf: int = 7
    maximum_sf: int = 12
    window_size: int = 5
    success_history: deque[bool] = field(default_factory=deque)

    def next_spreading_factor(self, current_sf: int, delivered: bool) -> int:
        self.success_history.append(delivered)
        while len(self.success_history) > self.window_size:
            self.success_history.popleft()

        success_rate = sum(self.success_history) / len(self.success_history)
        if success_rate > 0.9 and current_sf > self.minimum_sf:
            return current_sf - 1
        if success_rate < 0.6 and current_sf < self.maximum_sf:
            return current_sf + 1
        return current_sf
