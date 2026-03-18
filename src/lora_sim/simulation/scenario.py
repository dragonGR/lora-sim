from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

from lora_sim.domain.channel import ChannelModel
from lora_sim.domain.enums import NodeRole
from lora_sim.domain.node import Node, TrafficProfile
from lora_sim.domain.radio import PowerProfile, RadioConfig
from lora_sim.models.retry import RetryPolicy


@dataclass(slots=True)
class AckModel:
    enabled: bool = True
    rx1_delay_seconds: float = 1.0
    payload_size_bytes: int = 2
    downlink_interference_probability: float = 0.01


@dataclass(slots=True)
class Scenario:
    name: str
    duration_seconds: float
    seed: int
    channel: ChannelModel
    ack_model: AckModel = field(default_factory=AckModel)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    nodes: list[Node] = field(default_factory=list)

    def validate(self) -> None:
        if not self.nodes:
            raise ValueError("Scenario must define at least one node")
        gateway_count = sum(node.role == NodeRole.GATEWAY for node in self.nodes)
        if gateway_count == 0:
            raise ValueError("Scenario must define at least one gateway node")
        for node in self.nodes:
            node.radio.validate()
            if node.traffic and node.traffic.packet_count < 0:
                raise ValueError(f"Node {node.node_id} has negative packet count")

    def node_map(self) -> dict[str, Node]:
        return {node.node_id: node for node in self.nodes}


def load_scenario(path: str | Path) -> Scenario:
    raw = json.loads(Path(path).read_text())
    channel = ChannelModel(**raw.get("channel", {}))
    ack_model = AckModel(**raw.get("ack_model", {}))
    retry_policy = RetryPolicy(**raw.get("retry_policy", {}))
    nodes = [_parse_node(node_raw) for node_raw in raw["nodes"]]
    scenario = Scenario(
        name=raw["name"],
        duration_seconds=raw.get("duration_seconds", 60.0),
        seed=raw.get("seed", 42),
        channel=channel,
        ack_model=ack_model,
        retry_policy=retry_policy,
        nodes=nodes,
    )
    scenario.validate()
    return scenario


def _parse_node(raw: dict[str, object]) -> Node:
    traffic_raw = raw.get("traffic")
    traffic = TrafficProfile(**traffic_raw) if isinstance(traffic_raw, dict) else None
    radio_raw = dict(raw.get("radio", {}))
    power_profile_raw = radio_raw.pop("power_profile", None)
    power_profile = (
        PowerProfile(**power_profile_raw)
        if isinstance(power_profile_raw, dict)
        else PowerProfile()
    )
    return Node(
        node_id=str(raw["node_id"]),
        x_m=float(raw.get("x_m", 0.0)),
        y_m=float(raw.get("y_m", 0.0)),
        role=NodeRole(str(raw.get("role", "end_device"))),
        radio=RadioConfig(power_profile=power_profile, **radio_raw),
        traffic=traffic,
        tags={str(key): str(value) for key, value in raw.get("tags", {}).items()},
    )
