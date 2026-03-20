from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass(slots=True)
class AdrController:
    minimum_sf: int = 7
    maximum_sf: int = 12
    window_size: int = 5
    success_history: deque[bool] = field(default_factory=deque)
    gateway_history: deque[str] = field(default_factory=deque)

    def next_spreading_factor(
        self,
        current_sf: int,
        delivered: bool,
        selected_gateway_id: str | None = None,
    ) -> int:
        self.success_history.append(delivered)
        while len(self.success_history) > self.window_size:
            self.success_history.popleft()
        if selected_gateway_id is not None:
            self.gateway_history.append(selected_gateway_id)
            while len(self.gateway_history) > self.window_size:
                self.gateway_history.popleft()

        success_rate = sum(self.success_history) / len(self.success_history)
        stable_gateway = len(set(self.gateway_history)) <= 1 if self.gateway_history else False
        if success_rate > 0.9 and current_sf > self.minimum_sf:
            if stable_gateway or len(self.gateway_history) < 2:
                return current_sf - 1
        if success_rate < 0.6 and current_sf < self.maximum_sf:
            return current_sf + 1
        if not stable_gateway and len(self.gateway_history) >= self.window_size // 2 and current_sf < self.maximum_sf:
            return current_sf + 1
        return current_sf
