from __future__ import annotations

from pathlib import Path

from lora_sim.domain.metrics import SimulationMetrics
from lora_sim.io.result_writer import write_csv_results, write_json_results
from lora_sim.simulation.engine import SimulationEngine
from lora_sim.simulation.scenario import Scenario, load_scenario


def run_scenario(scenario: Scenario | str | Path, output_path: str | Path | None = None) -> SimulationMetrics:
    loaded = load_scenario(scenario) if isinstance(scenario, (str, Path)) else scenario
    engine = SimulationEngine(loaded)
    metrics = engine.run()
    if output_path is not None:
        output = Path(output_path)
        if output.suffix == ".csv":
            write_csv_results(metrics, output)
        else:
            write_json_results(metrics, output)
    return metrics
