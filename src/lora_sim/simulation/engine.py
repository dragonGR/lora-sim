from __future__ import annotations

from dataclasses import replace
import random

from lora_sim.domain.metrics import NodeEnergyProfile, PacketRecord, SimulationMetrics
from lora_sim.domain.packet import Packet
from lora_sim.domain.radio import RadioConfig
from lora_sim.models.adr import AdrController
from lora_sim.models.corruption import maybe_corrupt_packet
from lora_sim.models.interference import ActiveTransmission, evaluate_gateway_reception
from lora_sim.models.propagation import (
    meets_link_budget,
    received_signal_strength_dbm,
    snr_db,
)
from lora_sim.simulation.event_queue import EventQueue, ScheduledEvent
from lora_sim.simulation.scenario import Scenario


class SimulationEngine:
    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self.rng = random.Random(scenario.seed)
        self.metrics = SimulationMetrics(scenario_name=scenario.name, seed=scenario.seed)
        self.queue = EventQueue()
        self._active_transmissions: list[ActiveTransmission] = []
        self._event_priority = 0
        self._node_map = scenario.node_map()
        self._adr_by_node: dict[str, AdrController] = {}
        self._initialize_node_energy()

    def run(self) -> SimulationMetrics:
        self._schedule_initial_transmissions()
        while self.queue:
            event = self.queue.pop()
            match event.event_type:
                case "transmit":
                    self._handle_transmit(event.payload)
                case "complete":
                    self._handle_complete(event.payload)
                case _:
                    raise ValueError(f"Unknown event type: {event.event_type}")
        self._finalize_node_energy()
        return self.metrics

    def _initialize_node_energy(self) -> None:
        for node in self.scenario.nodes:
            self.metrics.node_energy[node.node_id] = NodeEnergyProfile()

    def _schedule_initial_transmissions(self) -> None:
        for node in self.scenario.nodes:
            traffic = node.traffic
            if traffic is None:
                continue
            for index in range(traffic.packet_count):
                start_time = traffic.start_time_seconds + index * traffic.interval_seconds
                if start_time > self.scenario.duration_seconds:
                    continue
                packet = Packet(
                    packet_id=f"{node.node_id}-{index + 1}",
                    source_id=node.node_id,
                    destination_id=traffic.destination_id,
                    created_at=start_time,
                    payload=self.rng.randbytes(traffic.payload_size_bytes),
                )
                self._push("transmit", start_time, {"packet": packet, "attempt": 1})

    def _handle_transmit(self, payload: dict[str, object]) -> None:
        packet = payload["packet"]
        attempt = int(payload["attempt"])
        assert isinstance(packet, Packet)

        source = self._node_map[packet.source_id]
        destination = self._node_map[packet.destination_id]
        radio = self._radio_for_attempt(source.node_id, source.radio)
        distance_m = source.distance_to(destination)
        airtime_seconds = radio.airtime_seconds(packet.size_bytes)
        tx_start_seconds = packet.created_at + (attempt - 1) * self.scenario.retry_policy.backoff_seconds
        tx_end_seconds = tx_start_seconds + airtime_seconds
        rssi_dbm = received_signal_strength_dbm(radio, distance_m, self.scenario.channel)
        snr_value_db = snr_db(rssi_dbm, self.scenario.channel)
        reception = evaluate_gateway_reception(
            active=self._active_transmissions,
            candidate_packet_id=packet.packet_id,
            candidate_destination_id=packet.destination_id,
            candidate_start_seconds=tx_start_seconds,
            candidate_end_seconds=tx_end_seconds,
            candidate_frequency_hz=radio.frequency_hz,
            candidate_rssi_dbm=rssi_dbm,
            candidate_spreading_factor=radio.spreading_factor,
            channel=self.scenario.channel,
        )
        interfered = self.rng.random() < self.scenario.channel.interference_probability
        self._record_tx_energy(packet.source_id, airtime_seconds)
        self._record_rx_energy(packet.destination_id, airtime_seconds)

        self._active_transmissions.append(
            ActiveTransmission(
                packet_id=packet.packet_id,
                source_id=packet.source_id,
                destination_id=packet.destination_id,
                start_seconds=tx_start_seconds,
                end_seconds=tx_end_seconds,
                frequency_hz=radio.frequency_hz,
                rssi_dbm=rssi_dbm,
                spreading_factor=radio.spreading_factor,
            )
        )
        self._push(
            "complete",
            tx_end_seconds,
            {
                "packet": packet,
                "attempt": attempt,
                "radio": radio,
                "distance_m": distance_m,
                "tx_start_seconds": tx_start_seconds,
                "tx_end_seconds": tx_end_seconds,
                "airtime_seconds": airtime_seconds,
                "snr_db": snr_value_db,
                "rssi_dbm": rssi_dbm,
                "collided": reception.collided,
                "path_limited": reception.path_limited,
                "overlap_count": reception.overlap_count,
                "dominant_interferer_db": reception.dominant_interferer_db,
                "interfered": interfered,
            },
        )

    def _handle_complete(self, payload: dict[str, object]) -> None:
        packet = payload["packet"]
        attempt = int(payload["attempt"])
        radio = payload["radio"]
        distance_m = float(payload["distance_m"])
        tx_start_seconds = float(payload["tx_start_seconds"])
        tx_end_seconds = float(payload["tx_end_seconds"])
        airtime_seconds = float(payload["airtime_seconds"])
        snr_value_db = float(payload["snr_db"])
        rssi_dbm = float(payload["rssi_dbm"])
        collided = bool(payload["collided"])
        path_limited = bool(payload["path_limited"])
        overlap_count = int(payload["overlap_count"])
        dominant_interferer_db = float(payload["dominant_interferer_db"])
        interfered = bool(payload["interfered"])
        assert isinstance(packet, Packet)
        assert isinstance(radio, RadioConfig)

        self._active_transmissions = [
            tx for tx in self._active_transmissions if tx.packet_id != packet.packet_id
        ]

        corrupted_packet, corrupted = maybe_corrupt_packet(packet, self.rng, self.scenario.channel)
        link_budget_ok = meets_link_budget(radio, snr_value_db, self.scenario.channel)
        delivered = link_budget_ok and not collided and not interfered and corrupted_packet.is_valid()

        reason = "delivered"
        if not link_budget_ok:
            reason = "link_budget"
        if path_limited:
            reason = "demodulation_paths"
        elif collided:
            reason = "collision"
        elif interfered:
            reason = "interference"
        elif corrupted:
            reason = "corruption"
        elif delivered:
            reason = "delivered"

        record = PacketRecord(
            packet_id=packet.packet_id,
            source_id=packet.source_id,
            destination_id=packet.destination_id,
            attempt=attempt,
            tx_start_seconds=tx_start_seconds,
            tx_end_seconds=tx_end_seconds,
            delivery_latency_seconds=tx_end_seconds - packet.created_at,
            airtime_seconds=airtime_seconds,
            distance_m=distance_m,
            snr_db=snr_value_db,
            rssi_dbm=rssi_dbm,
            delivered=delivered,
            collided=collided,
            corrupted=corrupted,
            interfered=interfered,
            path_limited=path_limited,
            overlap_count=overlap_count,
            dominant_interferer_db=dominant_interferer_db,
            spreading_factor=radio.spreading_factor,
            reason=reason,
        )
        self.metrics.record_packet(record)

        controller = self._adr_by_node.setdefault(packet.source_id, AdrController())
        next_sf = controller.next_spreading_factor(radio.spreading_factor, delivered)
        if next_sf != self._node_map[packet.source_id].radio.spreading_factor:
            self._node_map[packet.source_id].radio = replace(
                self._node_map[packet.source_id].radio,
                spreading_factor=next_sf,
            )

        if delivered or attempt >= self.scenario.retry_policy.max_attempts:
            return

        retry_payload = {"packet": packet, "attempt": attempt + 1}
        retry_time = tx_end_seconds + self.scenario.retry_policy.backoff_seconds
        self._push("transmit", retry_time, retry_payload)

    def _radio_for_attempt(self, node_id: str, fallback: RadioConfig) -> RadioConfig:
        node = self._node_map[node_id]
        return node.radio if node.radio else fallback

    def _push(self, event_type: str, event_time: float, payload: dict[str, object]) -> None:
        self._event_priority += 1
        self.queue.push(
            ScheduledEvent(
                event_time=event_time,
                priority=self._event_priority,
                event_type=event_type,
                payload=payload,
            )
        )

    def _record_tx_energy(self, node_id: str, airtime_seconds: float) -> None:
        node = self._node_map[node_id]
        profile = self.metrics.node_energy[node_id]
        profile.tx_airtime_seconds += airtime_seconds
        profile.tx_energy_joules += node.radio.power_profile.joules_for_tx(airtime_seconds)

    def _record_rx_energy(self, node_id: str, airtime_seconds: float) -> None:
        node = self._node_map[node_id]
        profile = self.metrics.node_energy[node_id]
        profile.rx_airtime_seconds += airtime_seconds
        profile.rx_energy_joules += node.radio.power_profile.joules_for_rx(airtime_seconds)

    def _finalize_node_energy(self) -> None:
        for node_id, profile in self.metrics.node_energy.items():
            node = self._node_map[node_id]
            active_time = profile.tx_airtime_seconds + profile.rx_airtime_seconds
            idle_time = max(self.scenario.duration_seconds - active_time, 0.0)
            profile.idle_time_seconds = idle_time
            profile.idle_energy_joules = node.radio.power_profile.joules_for_idle(idle_time)
