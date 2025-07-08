import time
import argparse
import matplotlib.pyplot as plt
from config import SPREADING_FACTORS
from utils import generate_packet, simulate_packet_delivery, verify_crc

def adjust_spreading_factor(current_sf, recent_success_rate):
    """Simulate Adaptive Data Rate (ADR)"""
    if recent_success_rate > 0.9 and current_sf > SPREADING_FACTORS[0]:
        return current_sf - 1  # Improve data rate
    elif recent_success_rate < 0.6 and current_sf < SPREADING_FACTORS[-1]:
        return current_sf + 1  # Improve reliability
    return current_sf  # No change

def sender_node(packets_to_send, receiver, initial_sf=7, verbose=True):
    print(f"[Sender] Starting transmission with initial SF={initial_sf}")
    ack_packets = []
    corrupted_count = 0
    sf = initial_sf
    history = []

    for i, pkt in enumerate(packets_to_send):
        attempts = 0
        delivered = False
        while attempts < 3 and not delivered:
            if verbose:
                print(f"Packet {i+1}, Attempt {attempts+1}: Transmitting (SF={sf})...")
            success, received_pkt = receiver.receive(pkt, sf=sf)

            if success and received_pkt is not None:
                if verify_crc(received_pkt):
                    if verbose:
                        print("✅ Packet delivered successfully and CRC matched.")
                    ack_packets.append(received_pkt)
                    delivered = True
                else:
                    corrupted_count += 1
                    if verbose:
                        print("❌ CRC mismatch: Packet was corrupted.")
                    attempts += 1
            else:
                if verbose:
                    print("❌ Delivery failed. Retrying...")
                attempts += 1

            time.sleep(0.1)

        history.append(delivered)
        if len(history) > 5:
            history.pop(0)

        avg_success = sum(history) / len(history) if history else 0
        sf = adjust_spreading_factor(sf, avg_success)

        if not delivered and verbose:
            print("🚫 Packet lost after 3 attempts.")

    return ack_packets, corrupted_count

class ReceiverNode:
    def __init__(self, distance=1000):
        self.distance = distance  # in meters

    def receive(self, packet, sf=7):
        return simulate_packet_delivery(
            packet,
            self.distance,
            sf=sf,
            noise_level=self.noise_level if hasattr(self, 'noise_level') else 0
        )

def run_distance_sweep(distances, packets_per_run=10, noise_level=0.0):
    results = []
    for distance in distances:
        print(f"\n--- Testing at {distance} meters ---")
        receiver = ReceiverNode(distance=distance)
        receiver.noise_level = noise_level
        packets = [generate_packet() for _ in range(packets_per_run)]
        ack_packets, _ = sender_node(packets, receiver, verbose=False)
        delivery_rate = len(ack_packets) / len(packets) * 100
        results.append((distance, delivery_rate))
    return results

def plot_results(results):
    distances = [r[0] for r in results]
    rates = [r[1] for r in results]

    plt.figure(figsize=(10, 6))
    plt.plot(distances, rates, marker='o', linestyle='-', color='b')
    plt.title('LoRa Packet Delivery Rate vs Distance')
    plt.xlabel('Distance (meters)')
    plt.ylabel('Delivery Rate (%)')
    plt.grid(True)
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.savefig('delivery_vs_distance.png')
    print("\n📊 Plot saved as 'delivery_vs_distance.png'")
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate LoRa communication with ADR and noise")
    parser.add_argument("--distance", type=int, default=3000, help="Distance in meters (default: 3000)")
    parser.add_argument("--sf", type=int, choices=SPREADING_FACTORS, default=10, help="Initial spreading factor")
    parser.add_argument("--packets", type=int, default=10, help="Number of packets to send")
    parser.add_argument("--noise", type=float, default=0.0, help="Noise level [0.0 to 1.0]")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-packet output")
    parser.add_argument("--plot", action="store_true", help="Run distance sweep and plot delivery rate")

    args = parser.parse_args()

    if args.plot:
        DISTANCE_SWEEP = list(range(1000, 11000, 1000))  # From 1000m to 10000m
        results = run_distance_sweep(DISTANCE_SWEEP, packets_per_run=10, noise_level=args.noise)
        plot_results(results)
    else:
        # Set noise level
        receiver = ReceiverNode(distance=args.distance)
        receiver.noise_level = args.noise

        # Generate packets
        packets = [generate_packet() for _ in range(args.packets)]

        # Send packets
        ack_packets, corrupted_count = sender_node(packets, receiver, initial_sf=args.sf, verbose=not args.quiet)

        print("\n[Summary]")
        print(f"Packets Sent: {len(packets)}")
        print(f"Packets Received: {len(ack_packets)}")
        print(f"Packets Corrupted: {corrupted_count}")
        print(f"Delivery Rate: {len(ack_packets)/len(packets)*100:.2f}%")
