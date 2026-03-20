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
    uplink_delivered: bool
    ack_requested: bool
    ack_received: bool
    ack_gateway_id: str | None
    ack_latency_seconds: float
    ack_window: str | None
    collided: bool
    corrupted: bool
    interfered: bool
    path_limited: bool
    overlap_count: int
    dominant_interferer_db: float
    selected_gateway_id: str | None
    candidate_gateway_count: int
    duty_cycle_wait_seconds: float
    channel_busy_wait_seconds: float
    spreading_factor: int
    reason: str


@dataclass(slots=True)
class NodeEnergyProfile:
    tx_airtime_seconds: float = 0.0
    rx_airtime_seconds: float = 0.0
    idle_time_seconds: float = 0.0
    tx_energy_joules: float = 0.0
    rx_energy_joules: float = 0.0
    idle_energy_joules: float = 0.0

    @property
    def total_energy_joules(self) -> float:
        return self.tx_energy_joules + self.rx_energy_joules + self.idle_energy_joules


@dataclass(slots=True)
class SimulationMetrics:
    scenario_name: str
    seed: int
    packets_sent: int = 0
    packets_delivered: int = 0
    packets_lost: int = 0
    uplinks_delivered: int = 0
    collisions: int = 0
    corruptions: int = 0
    interference_losses: int = 0
    retries: int = 0
    ack_requests: int = 0
    ack_successes: int = 0
    ack_failures: int = 0
    rx2_successes: int = 0
    duty_cycle_delays: int = 0
    channel_busy_delays: int = 0
    total_airtime_seconds: float = 0.0
    total_latency_seconds: float = 0.0
    total_duty_cycle_wait_seconds: float = 0.0
    total_channel_busy_wait_seconds: float = 0.0
    packet_records: list[PacketRecord] = field(default_factory=list)
    node_delivery: dict[str, dict[str, float | int]] = field(default_factory=dict)
    node_energy: dict[str, NodeEnergyProfile] = field(default_factory=dict)
    gateway_receptions: dict[str, dict[str, int]] = field(default_factory=dict)

    def record_packet(self, record: PacketRecord) -> None:
        self.packets_sent += 1
        self.total_airtime_seconds += record.airtime_seconds
        self.total_latency_seconds += record.delivery_latency_seconds
        self.total_duty_cycle_wait_seconds += record.duty_cycle_wait_seconds
        self.total_channel_busy_wait_seconds += record.channel_busy_wait_seconds
        self.packet_records.append(record)
        node_metrics = self.node_delivery.setdefault(
            record.source_id,
            {"sent": 0, "delivered": 0, "lost": 0},
        )
        node_metrics["sent"] += 1

        if record.attempt > 1:
            self.retries += 1
        if record.uplink_delivered:
            self.uplinks_delivered += 1
        if record.ack_requested:
            self.ack_requests += 1
        if record.ack_received:
            self.ack_successes += 1
            if record.ack_window == "rx2":
                self.rx2_successes += 1
        elif record.ack_requested:
            self.ack_failures += 1
        if record.duty_cycle_wait_seconds > 0:
            self.duty_cycle_delays += 1
        if record.channel_busy_wait_seconds > 0:
            self.channel_busy_delays += 1
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
        if record.selected_gateway_id is not None:
            gateway_metrics = self.gateway_receptions.setdefault(
                record.selected_gateway_id,
                {"uplinks": 0, "acks": 0},
            )
            if record.uplink_delivered:
                gateway_metrics["uplinks"] += 1
            if record.ack_received:
                gateway_metrics["acks"] += 1

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

    @property
    def total_energy_joules(self) -> float:
        return sum(profile.total_energy_joules for profile in self.node_energy.values())

    def to_dict(self) -> dict[str, object]:
        return {
            "scenario_name": self.scenario_name,
            "seed": self.seed,
            "packets_sent": self.packets_sent,
            "packets_delivered": self.packets_delivered,
            "packets_lost": self.packets_lost,
            "uplinks_delivered": self.uplinks_delivered,
            "delivery_rate": self.delivery_rate,
            "collisions": self.collisions,
            "corruptions": self.corruptions,
            "interference_losses": self.interference_losses,
            "retries": self.retries,
            "ack_requests": self.ack_requests,
            "ack_successes": self.ack_successes,
            "ack_failures": self.ack_failures,
            "rx2_successes": self.rx2_successes,
            "duty_cycle_delays": self.duty_cycle_delays,
            "channel_busy_delays": self.channel_busy_delays,
            "total_airtime_seconds": self.total_airtime_seconds,
            "average_latency_seconds": self.average_latency_seconds,
            "total_duty_cycle_wait_seconds": self.total_duty_cycle_wait_seconds,
            "total_channel_busy_wait_seconds": self.total_channel_busy_wait_seconds,
            "total_energy_joules": self.total_energy_joules,
            "node_delivery": self.node_delivery,
            "gateway_receptions": self.gateway_receptions,
            "node_energy": {
                node_id: asdict(profile) | {"total_energy_joules": profile.total_energy_joules}
                for node_id, profile in self.node_energy.items()
            },
            "packet_records": [asdict(record) for record in self.packet_records],
        }
