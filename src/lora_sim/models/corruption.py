from __future__ import annotations

import random

from lora_sim.domain.channel import ChannelModel
from lora_sim.domain.packet import Packet


def maybe_corrupt_packet(
    packet: Packet,
    rng: random.Random,
    channel: ChannelModel,
) -> tuple[Packet, bool]:
    if packet.size_bytes == 0:
        return packet, False
    if rng.random() >= channel.corruption_probability:
        return packet, False
    byte_index = rng.randrange(packet.size_bytes)
    return packet.corrupt(byte_index), True
