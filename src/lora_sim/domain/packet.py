from __future__ import annotations

from dataclasses import dataclass, field
import zlib


@dataclass(frozen=True, slots=True)
class Packet:
    packet_id: str
    source_id: str
    destination_id: str
    created_at: float
    payload: bytes = field(repr=False)

    @property
    def size_bytes(self) -> int:
        return len(self.payload)

    @property
    def checksum(self) -> int:
        return zlib.crc32(self.payload) & 0xFFFFFFFF

    def is_valid(self) -> bool:
        return self.checksum == (zlib.crc32(self.payload) & 0xFFFFFFFF)

    def corrupt(self, byte_index: int) -> "Packet":
        mutable = bytearray(self.payload)
        mutable[byte_index] ^= 0xFF
        return Packet(
            packet_id=self.packet_id,
            source_id=self.source_id,
            destination_id=self.destination_id,
            created_at=self.created_at,
            payload=bytes(mutable),
        )
