# utils.py
import random
import zlib  # For CRC32

def generate_packet(length=16):
    """Generate a random packet with CRC32 checksum"""
    payload = bytes([random.randint(0, 255) for _ in range(length)])
    crc = zlib.crc32(payload) & 0xFFFFFFFF  # 32-bit unsigned
    return {
        'payload': payload,
        'crc': crc
    }

def verify_crc(packet):
    """Verify the CRC32 of a received packet"""
    if packet is None or not isinstance(packet, dict) or 'payload' not in packet or 'crc' not in packet:
        return False
    payload = packet['payload']
    expected_crc = packet['crc']
    actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
    return expected_crc == actual_crc

def simulate_packet_delivery(packet, distance, sf=7, noise_level=0.0):
    """
    Simulate packet delivery with optional channel noise
    noise_level: float between 0 and 1 (e.g., 0.2 = 20% extra corruption)
    """
    base_success_rate = 0.95 if sf >= 10 else 0.85
    loss_factor = max(0, 1 - distance / 10000)
    success_rate = base_success_rate * loss_factor - noise_level * 0.3
    success_rate = max(0, min(1, success_rate))

    success = random.random() < success_rate

    if success:
        # Occasionally corrupt the packet even if delivered
        if random.random() < 0.05 + noise_level * 0.1:
            corrupted_payload = bytearray(packet['payload'])
            corrupted_payload[random.randint(0, len(corrupted_payload)-1)] ^= 0xFF
            return True, {'payload': bytes(corrupted_payload), 'crc': packet['crc']}
        # Return a properly structured packet
        return True, {
            'payload': packet['payload'],
            'crc': packet['crc']
        }
    else:
        return False, None
