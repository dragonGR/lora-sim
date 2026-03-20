from __future__ import annotations

from copy import deepcopy
from dataclasses import is_dataclass

from lora_sim.app.runner import run_scenario
from lora_sim.domain.metrics import SimulationMetrics
from lora_sim.simulation.scenario import Scenario, load_scenario


def compare_scenarios(
    left: Scenario | str,
    right: Scenario | str,
    seed: int | None = None,
) -> tuple[SimulationMetrics, SimulationMetrics]:
    left_scenario = load_scenario(left) if isinstance(left, str) else deepcopy(left)
    right_scenario = load_scenario(right) if isinstance(right, str) else deepcopy(right)
    if seed is not None:
        left_scenario.seed = seed
        right_scenario.seed = seed
    return run_scenario(left_scenario), run_scenario(right_scenario)


def sweep_scenario(
    scenario: Scenario | str,
    parameter_path: str,
    start: float,
    stop: float,
    step: float,
    seed: int | None = None,
) -> list[dict[str, float | int | str]]:
    loaded = load_scenario(scenario) if isinstance(scenario, str) else deepcopy(scenario)
    results: list[dict[str, float | int | str]] = []
    value = start
    while value <= stop + (step / 1000):
        variant = deepcopy(loaded)
        if seed is not None:
            variant.seed = seed
        set_parameter(variant, parameter_path, value)
        metrics = run_scenario(variant)
        results.append(
            {
                "scenario_name": variant.name,
                "parameter": parameter_path,
                "value": value,
                "packets_sent": metrics.packets_sent,
                "packets_delivered": metrics.packets_delivered,
                "ack_successes": metrics.ack_successes,
                "rx2_successes": metrics.rx2_successes,
                "delivery_rate": metrics.delivery_rate,
                "collisions": metrics.collisions,
                "retries": metrics.retries,
                "total_energy_joules": metrics.total_energy_joules,
            }
        )
        value += step
    return results


def monte_carlo_scenario(
    scenario: Scenario | str,
    iterations: int,
    base_seed: int | None = None,
) -> dict[str, object]:
    loaded = load_scenario(scenario) if isinstance(scenario, str) else deepcopy(scenario)
    summaries: list[dict[str, float | int]] = []
    for offset in range(iterations):
        variant = deepcopy(loaded)
        variant.seed = (base_seed if base_seed is not None else loaded.seed) + offset
        metrics = run_scenario(variant)
        summaries.append(
            {
                "seed": variant.seed,
                "delivery_rate": metrics.delivery_rate,
                "collisions": metrics.collisions,
                "retries": metrics.retries,
                "ack_successes": metrics.ack_successes,
                "rx2_successes": metrics.rx2_successes,
                "total_energy_joules": metrics.total_energy_joules,
            }
        )
    return {
        "scenario_name": loaded.name,
        "iterations": iterations,
        "base_seed": base_seed if base_seed is not None else loaded.seed,
        "mean_delivery_rate": _mean(item["delivery_rate"] for item in summaries),
        "mean_collisions": _mean(item["collisions"] for item in summaries),
        "mean_retries": _mean(item["retries"] for item in summaries),
        "mean_ack_successes": _mean(item["ack_successes"] for item in summaries),
        "mean_rx2_successes": _mean(item["rx2_successes"] for item in summaries),
        "mean_total_energy_joules": _mean(item["total_energy_joules"] for item in summaries),
        "runs": summaries,
    }


def set_parameter(scenario: Scenario, path: str, raw_value: float) -> None:
    target: object = scenario
    parts = path.split(".")

    for part in parts[:-1]:
        if part == "nodes":
            target = scenario.nodes
            continue
        if isinstance(target, list):
            target = next(node for node in target if getattr(node, "node_id") == part)
            continue
        target = getattr(target, part)

    final_part = parts[-1]
    if isinstance(target, list):
        target = next(node for node in target if getattr(node, "node_id") == final_part)
        return

    current_value = getattr(target, final_part)
    coerced = _coerce_type(current_value, raw_value)
    setattr(target, final_part, coerced)


def _coerce_type(current_value: object, raw_value: float) -> object:
    if isinstance(current_value, int) and not isinstance(current_value, bool):
        return int(raw_value)
    if isinstance(current_value, float):
        return float(raw_value)
    if is_dataclass(current_value):
        return current_value
    return raw_value


def _mean(values) -> float:
    collected = list(values)
    if not collected:
        return 0.0
    return sum(collected) / len(collected)
