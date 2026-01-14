from __future__ import annotations

from dataclasses import dataclass

from lora_sim.domain.channel import ChannelModel
from lora_sim.domain.radio import RadioConfig


@dataclass(slots=True)
class ActiveTransmission:
    packet_id: str
    source_id: str
    start_seconds: float
    end_seconds: float
    frequency_hz: int
    rssi_dbm: float
    spreading_factor: int

    def overlaps(self, start_seconds: float, end_seconds: float) -> bool:
        return start_seconds < self.end_seconds and end_seconds > self.start_seconds


def detect_collision(
    active: list[ActiveTransmission],
    candidate_start_seconds: float,
    candidate_end_seconds: float,
    candidate_frequency_hz: int,
    candidate_rssi_dbm: float,
    channel: ChannelModel,
) -> bool:
    for transmission in active:
        same_channel = transmission.frequency_hz == candidate_frequency_hz
        overlapping = transmission.overlaps(candidate_start_seconds, candidate_end_seconds)
        close_power = abs(transmission.rssi_dbm - candidate_rssi_dbm) <= channel.capture_threshold_db
        if same_channel and overlapping and close_power:
            return True
    return False
