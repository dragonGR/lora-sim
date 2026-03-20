from __future__ import annotations

from dataclasses import replace
import random

from lora_sim.domain.enums import NodeRole
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
        self._preferred_gateway_by_node: dict[str, str] = {}
        self._next_node_tx_available: dict[str, float] = {}
        self._next_frequency_available: dict[int, float] = {}
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
                scheduled_time = traffic.start_time_seconds + index * traffic.interval_seconds
                if scheduled_time > self.scenario.duration_seconds:
                    continue
                packet = Packet(
                    packet_id=f"{node.node_id}-{index + 1}",
                    source_id=node.node_id,
                    destination_id=traffic.destination_id,
                    created_at=scheduled_time,
                    payload=self.rng.randbytes(traffic.payload_size_bytes),
                )
                self._push(
                    "transmit",
                    scheduled_time,
                    {
                        "packet": packet,
                        "attempt": 1,
                        "scheduled_time": scheduled_time,
                        "duty_cycle_wait_seconds": 0.0,
                        "channel_busy_wait_seconds": 0.0,
                    },
                )

    def _handle_transmit(self, payload: dict[str, object]) -> None:
        packet = payload["packet"]
        attempt = int(payload["attempt"])
        scheduled_time = float(payload.get("scheduled_time", packet.created_at))
        duty_cycle_wait_seconds = float(payload.get("duty_cycle_wait_seconds", 0.0))
        channel_busy_wait_seconds = float(payload.get("channel_busy_wait_seconds", 0.0))
        assert isinstance(packet, Packet)

        source = self._node_map[packet.source_id]
        radio = self._radio_for_attempt(source.node_id, source.radio)
        airtime_seconds = radio.airtime_seconds(packet.size_bytes)
        constrained_start_seconds, extra_duty_wait, extra_channel_wait = self._apply_mac_constraints(
            node_id=packet.source_id,
            frequency_hz=radio.frequency_hz,
            requested_start_seconds=scheduled_time,
            airtime_seconds=airtime_seconds,
        )
        if constrained_start_seconds > scheduled_time:
            self._push(
                "transmit",
                constrained_start_seconds,
                {
                    "packet": packet,
                    "attempt": attempt,
                    "scheduled_time": constrained_start_seconds,
                    "duty_cycle_wait_seconds": duty_cycle_wait_seconds + extra_duty_wait,
                    "channel_busy_wait_seconds": channel_busy_wait_seconds + extra_channel_wait,
                },
            )
            return

        tx_start_seconds = constrained_start_seconds
        tx_end_seconds = tx_start_seconds + airtime_seconds
        candidate_gateways = self._resolve_candidate_gateways(packet.destination_id)
        best_gateway, best_reception = self._select_gateway_reception(
            packet=packet,
            source=source,
            candidate_gateways=candidate_gateways,
            radio=radio,
            tx_start_seconds=tx_start_seconds,
            tx_end_seconds=tx_end_seconds,
        )
        interfered = self.rng.random() < self.scenario.channel.interference_probability
        self._reserve_mac_resources(
            node_id=packet.source_id,
            frequency_hz=radio.frequency_hz,
            tx_end_seconds=tx_end_seconds,
            airtime_seconds=airtime_seconds,
        )
        self._record_tx_energy(packet.source_id, airtime_seconds)
        for gateway in candidate_gateways:
            self._record_rx_energy(gateway.node_id, airtime_seconds)

        tracked_gateway_id = best_gateway.node_id if best_gateway is not None else candidate_gateways[0].node_id
        tracked_rssi = best_reception["rssi_dbm"] if best_reception is not None else -999.0
        self._active_transmissions.append(
            ActiveTransmission(
                packet_id=packet.packet_id,
                source_id=packet.source_id,
                destination_id=tracked_gateway_id,
                start_seconds=tx_start_seconds,
                end_seconds=tx_end_seconds,
                frequency_hz=radio.frequency_hz,
                rssi_dbm=tracked_rssi,
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
                "distance_m": best_reception["distance_m"] if best_reception is not None else source.distance_to(candidate_gateways[0]),
                "tx_start_seconds": tx_start_seconds,
                "tx_end_seconds": tx_end_seconds,
                "airtime_seconds": airtime_seconds,
                "snr_db": best_reception["snr_db"] if best_reception is not None else -999.0,
                "rssi_dbm": tracked_rssi,
                "collided": best_reception["decision"].collided if best_reception is not None else True,
                "path_limited": best_reception["decision"].path_limited if best_reception is not None else False,
                "overlap_count": best_reception["decision"].overlap_count if best_reception is not None else 0,
                "dominant_interferer_db": best_reception["decision"].dominant_interferer_db if best_reception is not None else 0.0,
                "selected_gateway_id": best_gateway.node_id if best_gateway is not None else None,
                "candidate_gateway_count": len(candidate_gateways),
                "interfered": interfered,
                "confirmed_messages": bool(source.traffic and source.traffic.confirmed_messages),
                "duty_cycle_wait_seconds": duty_cycle_wait_seconds,
                "channel_busy_wait_seconds": channel_busy_wait_seconds,
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
        selected_gateway_id = payload["selected_gateway_id"]
        candidate_gateway_count = int(payload["candidate_gateway_count"])
        interfered = bool(payload["interfered"])
        confirmed_messages = bool(payload["confirmed_messages"])
        duty_cycle_wait_seconds = float(payload["duty_cycle_wait_seconds"])
        channel_busy_wait_seconds = float(payload["channel_busy_wait_seconds"])
        assert isinstance(packet, Packet)
        assert isinstance(radio, RadioConfig)

        self._active_transmissions = [
            transmission
            for transmission in self._active_transmissions
            if transmission.packet_id != packet.packet_id
        ]

        corrupted_packet, corrupted = maybe_corrupt_packet(packet, self.rng, self.scenario.channel)
        link_budget_ok = meets_link_budget(radio, snr_value_db, self.scenario.channel)
        uplink_delivered = (
            selected_gateway_id is not None
            and link_budget_ok
            and not collided
            and not interfered
            and corrupted_packet.is_valid()
        )
        ack_requested = confirmed_messages and self.scenario.ack_model.enabled and uplink_delivered
        if ack_requested:
            ack_received, ack_gateway_id, ack_latency_seconds, ack_window = self._resolve_ack(
                packet=packet,
                selected_gateway_id=selected_gateway_id,
                uplink_end_seconds=tx_end_seconds,
                source_radio=radio,
                confirmed_messages=confirmed_messages,
            )
        else:
            ack_received, ack_gateway_id, ack_latency_seconds, ack_window = False, None, 0.0, None
        delivered = uplink_delivered and (not ack_requested or ack_received)

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
        elif ack_requested and not ack_received:
            reason = "ack_timeout"

        record = PacketRecord(
            packet_id=packet.packet_id,
            source_id=packet.source_id,
            destination_id=packet.destination_id,
            attempt=attempt,
            tx_start_seconds=tx_start_seconds,
            tx_end_seconds=tx_end_seconds,
            delivery_latency_seconds=ack_latency_seconds if ack_received else tx_end_seconds - packet.created_at,
            airtime_seconds=airtime_seconds,
            distance_m=distance_m,
            snr_db=snr_value_db,
            rssi_dbm=rssi_dbm,
            delivered=delivered,
            uplink_delivered=uplink_delivered,
            ack_requested=ack_requested,
            ack_received=ack_received,
            ack_gateway_id=ack_gateway_id,
            ack_latency_seconds=ack_latency_seconds,
            ack_window=ack_window,
            collided=collided,
            corrupted=corrupted,
            interfered=interfered,
            path_limited=path_limited,
            overlap_count=overlap_count,
            dominant_interferer_db=dominant_interferer_db,
            selected_gateway_id=selected_gateway_id,
            candidate_gateway_count=candidate_gateway_count,
            duty_cycle_wait_seconds=duty_cycle_wait_seconds,
            channel_busy_wait_seconds=channel_busy_wait_seconds,
            spreading_factor=radio.spreading_factor,
            reason=reason,
        )
        self.metrics.record_packet(record)

        controller = self._adr_by_node.setdefault(packet.source_id, AdrController())
        next_sf = controller.next_spreading_factor(
            current_sf=radio.spreading_factor,
            delivered=delivered,
            selected_gateway_id=selected_gateway_id,
        )
        if selected_gateway_id is not None and uplink_delivered:
            self._preferred_gateway_by_node[packet.source_id] = selected_gateway_id
        if next_sf != self._node_map[packet.source_id].radio.spreading_factor:
            self._node_map[packet.source_id].radio = replace(
                self._node_map[packet.source_id].radio,
                spreading_factor=next_sf,
            )

        if delivered or attempt >= self.scenario.retry_policy.max_attempts:
            return

        retry_time = tx_end_seconds + self.scenario.retry_policy.backoff_seconds
        self._push(
            "transmit",
            retry_time,
            {
                "packet": packet,
                "attempt": attempt + 1,
                "scheduled_time": retry_time,
                "duty_cycle_wait_seconds": 0.0,
                "channel_busy_wait_seconds": 0.0,
            },
        )

    def _apply_mac_constraints(
        self,
        node_id: str,
        frequency_hz: int,
        requested_start_seconds: float,
        airtime_seconds: float,
    ) -> tuple[float, float, float]:
        node_ready_seconds = self._next_node_tx_available.get(node_id, 0.0)
        frequency_ready_seconds = (
            self._next_frequency_available.get(frequency_hz, 0.0)
            if self.scenario.channel.channel_guard_seconds > 0
            else 0.0
        )
        constrained_start_seconds = max(requested_start_seconds, node_ready_seconds, frequency_ready_seconds)
        duty_cycle_wait = max(node_ready_seconds - requested_start_seconds, 0.0)
        channel_busy_wait = max(frequency_ready_seconds - requested_start_seconds, 0.0)
        return constrained_start_seconds, duty_cycle_wait, channel_busy_wait

    def _reserve_mac_resources(
        self,
        node_id: str,
        frequency_hz: int,
        tx_end_seconds: float,
        airtime_seconds: float,
    ) -> None:
        duty_fraction = self.scenario.channel.duty_cycle_fraction
        if duty_fraction <= 0 or duty_fraction > 1:
            duty_fraction = 1.0
        off_time_seconds = airtime_seconds * ((1 / duty_fraction) - 1) if duty_fraction < 1.0 else 0.0
        self._next_node_tx_available[node_id] = tx_end_seconds + off_time_seconds
        if self.scenario.channel.channel_guard_seconds > 0:
            self._next_frequency_available[frequency_hz] = (
                tx_end_seconds + self.scenario.channel.channel_guard_seconds
            )

    def _radio_for_attempt(self, node_id: str, fallback: RadioConfig) -> RadioConfig:
        node = self._node_map[node_id]
        return node.radio if node.radio else fallback

    def _resolve_candidate_gateways(self, destination_id: str) -> list:
        if destination_id in self._node_map:
            return [self._node_map[destination_id]]
        gateways = [node for node in self.scenario.nodes if node.role == NodeRole.GATEWAY]
        if not gateways:
            raise ValueError("Scenario has no gateways")
        return gateways

    def _select_gateway_reception(
        self,
        packet: Packet,
        source,
        candidate_gateways: list,
        radio: RadioConfig,
        tx_start_seconds: float,
        tx_end_seconds: float,
    ):
        preferred_gateway_id = self._preferred_gateway_by_node.get(packet.source_id)
        best_gateway = None
        best_reception = None
        best_score = None
        for gateway in candidate_gateways:
            distance_m = source.distance_to(gateway)
            rssi_dbm = received_signal_strength_dbm(radio, distance_m, self.scenario.channel)
            snr_value_db = snr_db(rssi_dbm, self.scenario.channel)
            decision = evaluate_gateway_reception(
                active=self._active_transmissions,
                candidate_packet_id=packet.packet_id,
                candidate_destination_id=gateway.node_id,
                candidate_start_seconds=tx_start_seconds,
                candidate_end_seconds=tx_end_seconds,
                candidate_frequency_hz=radio.frequency_hz,
                candidate_rssi_dbm=rssi_dbm,
                candidate_spreading_factor=radio.spreading_factor,
                channel=self.scenario.channel,
            )
            reception = {
                "gateway": gateway,
                "distance_m": distance_m,
                "rssi_dbm": rssi_dbm,
                "snr_db": snr_value_db,
                "decision": decision,
            }
            score = (
                int(not decision.collided and not decision.path_limited),
                int(gateway.node_id == preferred_gateway_id),
                rssi_dbm,
            )
            if best_score is None or score > best_score:
                best_score = score
                best_gateway = gateway
                best_reception = reception
        return best_gateway, best_reception

    def _resolve_ack(
        self,
        packet: Packet,
        selected_gateway_id: str | None,
        uplink_end_seconds: float,
        source_radio: RadioConfig,
        confirmed_messages: bool,
    ) -> tuple[bool, str | None, float, str | None]:
        if not confirmed_messages or not self.scenario.ack_model.enabled or selected_gateway_id is None:
            return False, None, 0.0, None

        gateway = self._node_map[selected_gateway_id]
        rx1_received, rx1_latency = self._attempt_ack_window(
            gateway=gateway,
            source=self._node_map[packet.source_id],
            packet_created_at=packet.created_at,
            source_radio=source_radio,
            delay_seconds=self.scenario.ack_model.rx1_delay_seconds,
            frequency_hz=gateway.radio.frequency_hz,
            spreading_factor=source_radio.spreading_factor,
            interference_probability=self.scenario.ack_model.downlink_interference_probability,
            uplink_end_seconds=uplink_end_seconds,
        )
        if rx1_received:
            return True, gateway.node_id, rx1_latency, "rx1"

        if not self.scenario.ack_model.rx2_enabled:
            return False, gateway.node_id, 0.0, None

        rx2_received, rx2_latency = self._attempt_ack_window(
            gateway=gateway,
            source=self._node_map[packet.source_id],
            packet_created_at=packet.created_at,
            source_radio=replace(
                source_radio,
                frequency_hz=self.scenario.ack_model.rx2_frequency_hz,
                spreading_factor=self.scenario.ack_model.rx2_spreading_factor,
            ),
            delay_seconds=self.scenario.ack_model.rx2_delay_seconds,
            frequency_hz=self.scenario.ack_model.rx2_frequency_hz,
            spreading_factor=self.scenario.ack_model.rx2_spreading_factor,
            interference_probability=0.0,
            uplink_end_seconds=uplink_end_seconds,
        )
        if rx2_received:
            return True, gateway.node_id, rx2_latency, "rx2"
        return False, gateway.node_id, 0.0, None

    def _attempt_ack_window(
        self,
        gateway,
        source,
        packet_created_at: float,
        source_radio: RadioConfig,
        delay_seconds: float,
        frequency_hz: int,
        spreading_factor: int,
        interference_probability: float,
        uplink_end_seconds: float,
    ) -> tuple[bool, float]:
        ack_radio = replace(
            gateway.radio,
            frequency_hz=frequency_hz,
            spreading_factor=spreading_factor,
        )
        ack_start_seconds = uplink_end_seconds + delay_seconds
        ack_airtime_seconds = ack_radio.airtime_seconds(self.scenario.ack_model.payload_size_bytes)
        ack_end_seconds = ack_start_seconds + ack_airtime_seconds
        downlink_rssi_dbm = received_signal_strength_dbm(
            ack_radio,
            gateway.distance_to(source),
            self.scenario.channel,
        )
        downlink_snr_db = snr_db(downlink_rssi_dbm, self.scenario.channel)
        downlink_ok = meets_link_budget(source_radio, downlink_snr_db, self.scenario.channel)
        interfered = self.rng.random() < interference_probability
        self._record_tx_energy(gateway.node_id, ack_airtime_seconds)
        self._record_rx_energy(source.node_id, ack_airtime_seconds)
        ack_received = downlink_ok and not interfered and ack_end_seconds <= self.scenario.duration_seconds
        ack_latency_seconds = ack_end_seconds - packet_created_at if ack_received else 0.0
        return ack_received, ack_latency_seconds

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
