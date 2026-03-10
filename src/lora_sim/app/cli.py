from __future__ import annotations

import argparse
import json
from pathlib import Path

from lora_sim.app.report import render_html_report, render_text_report
from lora_sim.app.runner import run_scenario
from lora_sim.io.result_writer import write_json_results
from lora_sim.simulation.experiments import compare_scenarios, monte_carlo_scenario, sweep_scenario
from lora_sim.simulation.scenario import load_scenario


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic LoRa network simulation toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a scenario file")
    run_parser.add_argument("scenario", help="Path to a scenario JSON file")
    run_parser.add_argument("--seed", type=int, help="Override scenario seed")
    run_parser.add_argument("--out", help="Write JSON or CSV results")
    run_parser.add_argument("--report", help="Write HTML report")

    sweep_parser = subparsers.add_parser("sweep", help="Run a parameter sweep against a scenario")
    sweep_parser.add_argument("scenario", help="Path to a scenario JSON file")
    sweep_parser.add_argument("--param", required=True, help="Parameter path, e.g. nodes.gateway.x_m")
    sweep_parser.add_argument(
        "--range",
        required=True,
        help="Numeric range in start:stop:step format",
    )
    sweep_parser.add_argument("--seed", type=int, help="Override scenario seed")
    sweep_parser.add_argument("--out", help="Write sweep results as JSON")

    compare_parser = subparsers.add_parser("compare", help="Run two scenarios and compare summaries")
    compare_parser.add_argument("left", help="Baseline scenario path")
    compare_parser.add_argument("right", help="Candidate scenario path")
    compare_parser.add_argument("--seed", type=int, help="Override both scenario seeds")

    monte_carlo_parser = subparsers.add_parser("monte-carlo", help="Run repeated simulations with rolling seeds")
    monte_carlo_parser.add_argument("scenario", help="Path to a scenario JSON file")
    monte_carlo_parser.add_argument("--iterations", type=int, required=True, help="Number of repeated runs")
    monte_carlo_parser.add_argument("--seed", type=int, help="Base seed for the first run")
    monte_carlo_parser.add_argument("--out", help="Write aggregate results as JSON")

    report_parser = subparsers.add_parser("report", help="Create an HTML report from a result JSON file")
    report_parser.add_argument("results", help="Path to a JSON result file")
    report_parser.add_argument("--out", required=True, help="Output HTML path")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        scenario = load_scenario(args.scenario)
        if args.seed is not None:
            scenario.seed = args.seed
        metrics = run_scenario(scenario, output_path=args.out)
        print(render_text_report(metrics))
        if args.report:
            Path(args.report).write_text(render_html_report(metrics))
        return 0

    if args.command == "sweep":
        start, stop, step = _parse_range(args.range)
        results = sweep_scenario(
            args.scenario,
            parameter_path=args.param,
            start=start,
            stop=stop,
            step=step,
            seed=args.seed,
        )
        print(_render_sweep_summary(results))
        if args.out:
            Path(args.out).write_text(json.dumps(results, indent=2))
        return 0

    if args.command == "compare":
        left_metrics, right_metrics = compare_scenarios(args.left, args.right, seed=args.seed)
        print(_render_compare_summary(left_metrics, right_metrics))
        return 0

    if args.command == "monte-carlo":
        results = monte_carlo_scenario(args.scenario, iterations=args.iterations, base_seed=args.seed)
        print(_render_monte_carlo_summary(results))
        if args.out:
            Path(args.out).write_text(json.dumps(results, indent=2))
        return 0

    if args.command == "report":
        raw = Path(args.results).read_text()
        Path(args.out).write_text(_json_results_to_html(raw))
        return 0

    parser.error("Unknown command")
    return 2


def _json_results_to_html(raw_json: str) -> str:
    data = json.loads(raw_json)
    from lora_sim.domain.metrics import SimulationMetrics

    metrics = SimulationMetrics(scenario_name=data["scenario_name"], seed=data["seed"])
    metrics.packets_sent = data["packets_sent"]
    metrics.packets_delivered = data["packets_delivered"]
    metrics.packets_lost = data["packets_lost"]
    metrics.collisions = data["collisions"]
    metrics.corruptions = data["corruptions"]
    metrics.interference_losses = data["interference_losses"]
    metrics.retries = data["retries"]
    metrics.total_airtime_seconds = data["total_airtime_seconds"]
    metrics.total_latency_seconds = data["average_latency_seconds"] * max(data["packets_sent"], 1)
    metrics.node_delivery = data.get("node_delivery", {})
    from lora_sim.domain.metrics import NodeEnergyProfile

    metrics.node_energy = {
        node_id: NodeEnergyProfile(
            tx_airtime_seconds=profile.get("tx_airtime_seconds", 0.0),
            rx_airtime_seconds=profile.get("rx_airtime_seconds", 0.0),
            idle_time_seconds=profile.get("idle_time_seconds", 0.0),
            tx_energy_joules=profile.get("tx_energy_joules", 0.0),
            rx_energy_joules=profile.get("rx_energy_joules", 0.0),
            idle_energy_joules=profile.get("idle_energy_joules", 0.0),
        )
        for node_id, profile in data.get("node_energy", {}).items()
    }
    return render_html_report(metrics)


def _parse_range(raw: str) -> tuple[float, float, float]:
    start, stop, step = raw.split(":")
    return float(start), float(stop), float(step)


def _render_sweep_summary(results: list[dict[str, float | int | str]]) -> str:
    lines = ["Sweep Results:"]
    for item in results:
        lines.append(
            "  "
            f"{item['parameter']}={item['value']}: "
            f"delivery={float(item['delivery_rate']) * 100:.2f}% "
            f"collisions={item['collisions']} retries={item['retries']}"
        )
    return "\n".join(lines)


def _render_compare_summary(left_metrics, right_metrics) -> str:
    delivery_delta = (right_metrics.delivery_rate - left_metrics.delivery_rate) * 100
    collision_delta = right_metrics.collisions - left_metrics.collisions
    retry_delta = right_metrics.retries - left_metrics.retries
    return "\n".join(
        [
            "Comparison:",
            f"  Left:  {left_metrics.scenario_name} delivery={left_metrics.delivery_rate * 100:.2f}% collisions={left_metrics.collisions} retries={left_metrics.retries} energy={left_metrics.total_energy_joules:.6f}J",
            f"  Right: {right_metrics.scenario_name} delivery={right_metrics.delivery_rate * 100:.2f}% collisions={right_metrics.collisions} retries={right_metrics.retries} energy={right_metrics.total_energy_joules:.6f}J",
            f"  Delta: delivery={delivery_delta:+.2f}pp collisions={collision_delta:+d} retries={retry_delta:+d}",
        ]
    )


def _render_monte_carlo_summary(results: dict[str, object]) -> str:
    return "\n".join(
        [
            "Monte Carlo Results:",
            f"  Scenario: {results['scenario_name']}",
            f"  Iterations: {results['iterations']}",
            f"  Base Seed: {results['base_seed']}",
            f"  Mean Delivery: {float(results['mean_delivery_rate']) * 100:.2f}%",
            f"  Mean Collisions: {float(results['mean_collisions']):.2f}",
            f"  Mean Retries: {float(results['mean_retries']):.2f}",
            f"  Mean Energy: {float(results['mean_total_energy_joules']):.6f}J",
        ]
    )
