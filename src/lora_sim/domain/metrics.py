from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class PacketRecord:
    packet_id: str
    source_id: str
    destination_id: str
    attempt: int
    tx_start_seconds: float
    tx_end_seconds: float
    delivery_latency_seconds: float
    airtime_seconds: float
    distance_m: float
    snr_db: float
    rssi_dbm: float
    delivered: bool
    collided: bool
    corrupted: bool
    interfered: bool
    spreading_factor: int
    reason: str


@dataclass(slots=True)
class SimulationMetrics:
    scenario_name: str
    seed: int
    packets_sent: int = 0
    packets_delivered: int = 0
    packets_lost: int = 0
    collisions: int = 0
    corruptions: int = 0
    interference_losses: int = 0
    retries: int = 0
    total_airtime_seconds: float = 0.0
    total_latency_seconds: float = 0.0
    packet_records: list[PacketRecord] = field(default_factory=list)
    node_delivery: dict[str, dict[str, float | int]] = field(default_factory=dict)

    def record_packet(self, record: PacketRecord) -> None:
        self.packets_sent += 1
        self.total_airtime_seconds += record.airtime_seconds
        self.total_latency_seconds += record.delivery_latency_seconds
        self.packet_records.append(record)
        node_metrics = self.node_delivery.setdefault(
            record.source_id,
            {"sent": 0, "delivered": 0, "lost": 0},
        )
        node_metrics["sent"] += 1

        if record.attempt > 1:
            self.retries += 1
        if record.delivered:
            self.packets_delivered += 1
            node_metrics["delivered"] += 1
        else:
            self.packets_lost += 1
            node_metrics["lost"] += 1
        if record.collided:
            self.collisions += 1
        if record.corrupted:
            self.corruptions += 1
        if record.interfered:
            self.interference_losses += 1

    @property
    def delivery_rate(self) -> float:
        if self.packets_sent == 0:
            return 0.0
        return self.packets_delivered / self.packets_sent

    @property
    def average_latency_seconds(self) -> float:
        if self.packets_sent == 0:
            return 0.0
        return self.total_latency_seconds / self.packets_sent

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_name": self.scenario_name,
            "seed": self.seed,
            "packets_sent": self.packets_sent,
            "packets_delivered": self.packets_delivered,
            "packets_lost": self.packets_lost,
            "delivery_rate": self.delivery_rate,
            "collisions": self.collisions,
            "corruptions": self.corruptions,
            "interference_losses": self.interference_losses,
            "retries": self.retries,
            "total_airtime_seconds": self.total_airtime_seconds,
            "average_latency_seconds": self.average_latency_seconds,
            "node_delivery": self.node_delivery,
            "packet_records": [asdict(record) for record in self.packet_records],
        }
