# 📡 LoRa Communication Simulator

A realistic simulation of **LoRa (Long Range)** wireless communication between two nodes. This tool demonstrates key concepts in wireless networking, packet transmission, error detection, adaptive data rate (ADR), and channel interference modeling.

This simulator can be used for:
- Learning how LoRa works  
- Testing network behavior under noise and distance  
- Demonstrating understanding of wireless protocols  
- Visualizing performance trends using graphs  

---

## 🧠 Features

### ✅ Packet Generation with CRC32 Checksums
Each packet includes a CRC32 checksum to validate integrity upon reception.

### ✅ Wireless Signal Loss Based on Distance
Signal strength degrades realistically as the distance increases.

### ✅ Channel Noise / Interference Modeling
Simulates external interference by introducing random corruption.

### ✅ Adaptive Data Rate (ADR) Simulation
Automatically adjusts spreading factor based on link quality to optimize throughput or reliability.

### ✅ Retransmission Logic
Packets are retransmitted up to 3 times if not received correctly.

### ✅ CLI Interface
Run simulations directly from the terminal with customizable parameters.

### ✅ Delivery vs Distance Plotting
Visualize how delivery rate changes over distance using `matplotlib`.

---

## 📦 Requirements

Make sure you have the following installed:

```bash
pip install numpy matplotlib
```

> 💡 Note: Python 3.8+ is recommended.

---

## 🚀 How to Run

### 🔹 Basic Usage

Runs a default simulation at 3000 meters with 10 packets and SF=10.

```bash
python simulator.py
```

### 🔹 Custom Simulation

Example with custom settings:

```bash
python simulator.py --distance 5000 --packets 15 --sf 9 --noise 0.2
```

### 🔹 Run Distance Sweep and Plot Results

Generates a graph showing how delivery rate decreases with increasing distance.

```bash
python simulator.py --plot --noise 0.1
```

---

### 📋 Output Example

```text
[Summary]
Packets Sent: 10
Packets Received: 8
Packets Corrupted: 1
Packets Lost: 1
Delivery Rate: 80.00%
```

---

## 🚩 Command-Line Flags

| Flag           | Full Name             | Description                                      | Example                             |
|----------------|------------------------|--------------------------------------------------|-------------------------------------|
| `-h`           | `--help`               | Show help message and exit                       | `python simulator.py --help`        |
| `--distance`   | Distance in meters     | Simulated distance between sender and receiver   | `--distance 5000`                  |
| `--sf`         | Spreading Factor       | Initial spreading factor (7–12)                 | `--sf 9`                            |
| `--packets`    | Number of Packets      | Total number of packets to send                  | `--packets 20`                      |
| `--noise`      | Channel Noise Level    | Simulated channel noise [0.0 to 1.0]            | `--noise 0.3`                       |
| `--quiet`      | Quiet Mode             | Suppress per-packet output                       | `--quiet`                           |
| `--plot`       | Run Distance Sweep     | Run simulations at multiple distances            | `--plot`                            |

---

## ✅ Example Usage Commands

```bash
# Basic simulation with default settings
python simulator.py

# Custom simulation: 5000m, 15 packets, SF=9, moderate noise
python simulator.py --distance 5000 --packets 15 --sf 9 --noise 0.2

# Plot delivery rate across multiple distances
python simulator.py --plot --noise 0.1
```

---
