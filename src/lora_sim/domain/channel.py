from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChannelModel:
    noise_floor_dbm: float = -118.0
    path_loss_exponent: float = 2.7
    reference_distance_m: float = 1.0
    reference_loss_db: float = 32.0
    interference_probability: float = 0.02
    corruption_probability: float = 0.01
    snr_margin_db: float = 3.0
    capture_threshold_db: float = 6.0
    sf_orthogonality_margin_db: float = 10.0
    gateway_demodulation_paths: int = 8
    duty_cycle_fraction: float = 1.0
    channel_guard_seconds: float = 0.0
