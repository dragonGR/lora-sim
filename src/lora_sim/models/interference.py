from __future__ import annotations

from dataclasses import dataclass

from lora_sim.domain.channel import ChannelModel


@dataclass(slots=True)
class ActiveTransmission:
    packet_id: str
    source_id: str
    destination_id: str
    start_seconds: float
    end_seconds: float
    frequency_hz: int
    rssi_dbm: float
    spreading_factor: int

    def overlaps(self, start_seconds: float, end_seconds: float) -> bool:
        return start_seconds < self.end_seconds and end_seconds > self.start_seconds


@dataclass(frozen=True, slots=True)
class ReceptionDecision:
    collided: bool
    path_limited: bool
    dominant_interferer_db: float
    overlap_count: int


def evaluate_gateway_reception(
    active: list[ActiveTransmission],
    candidate_packet_id: str,
    candidate_destination_id: str,
    candidate_start_seconds: float,
    candidate_end_seconds: float,
    candidate_frequency_hz: int,
    candidate_rssi_dbm: float,
    candidate_spreading_factor: int,
    channel: ChannelModel,
) -> ReceptionDecision:
    overlapping = [
        transmission
        for transmission in active
        if transmission.packet_id != candidate_packet_id
        and transmission.destination_id == candidate_destination_id
        and transmission.frequency_hz == candidate_frequency_hz
        and transmission.overlaps(candidate_start_seconds, candidate_end_seconds)
    ]
    if not overlapping:
        return ReceptionDecision(
            collided=False,
            path_limited=False,
            dominant_interferer_db=0.0,
            overlap_count=0,
        )

    path_limited = len(overlapping) >= channel.gateway_demodulation_paths
    dominant_interferer_db = max(
        (transmission.rssi_dbm - candidate_rssi_dbm) for transmission in overlapping
    )
    collided = path_limited
    for transmission in active:
        if transmission.packet_id == candidate_packet_id:
            continue
        same_channel = transmission.frequency_hz == candidate_frequency_hz
        overlaps_in_time = transmission.overlaps(candidate_start_seconds, candidate_end_seconds)
        same_destination = transmission.destination_id == candidate_destination_id
        if not (same_channel and overlaps_in_time and same_destination):
            continue

        power_delta_db = candidate_rssi_dbm - transmission.rssi_dbm
        same_sf = transmission.spreading_factor == candidate_spreading_factor
        if same_sf and power_delta_db <= channel.capture_threshold_db:
            collided = True
            continue
        if not same_sf and power_delta_db <= -channel.sf_orthogonality_margin_db:
            collided = True

    return ReceptionDecision(
        collided=collided,
        path_limited=path_limited,
        dominant_interferer_db=dominant_interferer_db,
        overlap_count=len(overlapping),
    )
