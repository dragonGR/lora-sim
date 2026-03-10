from __future__ import annotations

import csv
from dataclasses import asdict
import json
from pathlib import Path

from lora_sim.domain.metrics import SimulationMetrics


def write_json_results(metrics: SimulationMetrics, path: str | Path) -> None:
    Path(path).write_text(json.dumps(metrics.to_dict(), indent=2))


def write_csv_results(metrics: SimulationMetrics, path: str | Path) -> None:
    with Path(path).open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "packet_id",
                "source_id",
                "destination_id",
                "attempt",
                "tx_start_seconds",
                "tx_end_seconds",
                "delivery_latency_seconds",
                "airtime_seconds",
                "distance_m",
                "snr_db",
                "rssi_dbm",
                "delivered",
                "collided",
                "corrupted",
                "interfered",
                "path_limited",
                "overlap_count",
                "dominant_interferer_db",
                "spreading_factor",
                "reason",
            ],
        )
        writer.writeheader()
        for record in metrics.packet_records:
            writer.writerow(asdict(record))
