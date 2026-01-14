from __future__ import annotations

from dataclasses import dataclass
from math import ceil


DEFAULT_CODING_RATE = "4/5"
SUPPORTED_SPREADING_FACTORS = tuple(range(7, 13))
SUPPORTED_BANDWIDTHS = (125_000, 250_000, 500_000)


@dataclass(frozen=True, slots=True)
class RadioConfig:
    frequency_hz: int = 868_100_000
    bandwidth_hz: int = 125_000
    spreading_factor: int = 9
    coding_rate: str = DEFAULT_CODING_RATE
    tx_power_dbm: int = 14
    preamble_symbols: int = 8
    explicit_header: bool = True
    crc_enabled: bool = True

    def validate(self) -> None:
        if self.spreading_factor not in SUPPORTED_SPREADING_FACTORS:
            msg = f"Unsupported spreading factor: {self.spreading_factor}"
            raise ValueError(msg)
        if self.bandwidth_hz not in SUPPORTED_BANDWIDTHS:
            msg = f"Unsupported bandwidth: {self.bandwidth_hz}"
            raise ValueError(msg)
        if self.coding_rate not in {"4/5", "4/6", "4/7", "4/8"}:
            msg = f"Unsupported coding rate: {self.coding_rate}"
            raise ValueError(msg)

    @property
    def coding_rate_denominator(self) -> int:
        return int(self.coding_rate.split("/")[1])

    def symbol_duration_seconds(self) -> float:
        return (2 ** self.spreading_factor) / self.bandwidth_hz

    def airtime_seconds(self, payload_size_bytes: int) -> float:
        low_data_rate_opt = int(
            self.spreading_factor >= 11 and self.bandwidth_hz == 125_000
        )
        header_disabled = 0 if self.explicit_header else 1
        crc = 1 if self.crc_enabled else 0
        sf = self.spreading_factor
        bw = self.bandwidth_hz
        cr = self.coding_rate_denominator - 4

        t_sym = (2**sf) / bw
        t_preamble = (self.preamble_symbols + 4.25) * t_sym

        numerator = 8 * payload_size_bytes - 4 * sf + 28 + 16 * crc - 20 * header_disabled
        denominator = 4 * (sf - 2 * low_data_rate_opt)
        payload_symbols = 8 + max(ceil(numerator / denominator) * (cr + 4), 0)
        t_payload = payload_symbols * t_sym
        return t_preamble + t_payload
