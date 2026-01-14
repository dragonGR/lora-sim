from __future__ import annotations

from dataclasses import dataclass, field

from .enums import NodeRole
from .radio import RadioConfig


@dataclass(frozen=True, slots=True)
class TrafficProfile:
    packet_count: int
    interval_seconds: float
    start_time_seconds: float = 0.0
    payload_size_bytes: int = 16
    destination_id: str = "gateway"


@dataclass(slots=True)
class Node:
    node_id: str
    x_m: float
    y_m: float
    role: NodeRole
    radio: RadioConfig
    traffic: TrafficProfile | None = None
    tags: dict[str, str] = field(default_factory=dict)

    def distance_to(self, other: "Node") -> float:
        dx = self.x_m - other.x_m
        dy = self.y_m - other.y_m
        return (dx * dx + dy * dy) ** 0.5
