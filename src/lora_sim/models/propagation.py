from __future__ import annotations

from math import log10

from lora_sim.domain.channel import ChannelModel
from lora_sim.domain.radio import RadioConfig


SNR_THRESHOLDS_BY_SF = {
    7: -7.5,
    8: -10.0,
    9: -12.5,
    10: -15.0,
    11: -17.5,
    12: -20.0,
}


def path_loss_db(distance_m: float, channel: ChannelModel) -> float:
    effective_distance = max(distance_m, channel.reference_distance_m)
    return channel.reference_loss_db + 10 * channel.path_loss_exponent * log10(
        effective_distance / channel.reference_distance_m
    )


def received_signal_strength_dbm(
    radio: RadioConfig,
    distance_m: float,
    channel: ChannelModel,
) -> float:
    return radio.tx_power_dbm - path_loss_db(distance_m, channel)


def snr_db(rssi_dbm: float, channel: ChannelModel) -> float:
    return rssi_dbm - channel.noise_floor_dbm


def meets_link_budget(radio: RadioConfig, snr_value_db: float, channel: ChannelModel) -> bool:
    threshold = SNR_THRESHOLDS_BY_SF[radio.spreading_factor] + channel.snr_margin_db
    return snr_value_db >= threshold
