import unittest

from lora_sim.app.runner import run_scenario
from lora_sim.simulation.experiments import monte_carlo_scenario


class MonteCarloTests(unittest.TestCase):
    def test_monte_carlo_returns_requested_run_count(self) -> None:
        result = monte_carlo_scenario(
            "scenarios/multi_node_collision.json",
            iterations=4,
            base_seed=30,
        )

        self.assertEqual(result["iterations"], 4)
        self.assertEqual(len(result["runs"]), 4)
        self.assertEqual(result["runs"][0]["seed"], 30)
        self.assertEqual(result["runs"][-1]["seed"], 33)

    def test_energy_is_exposed_in_run_results(self) -> None:
        metrics = run_scenario("scenarios/simple_link.json")

        self.assertIn("sensor-a", metrics.node_energy)
        self.assertGreater(metrics.node_energy["sensor-a"].total_energy_joules, 0.0)


if __name__ == "__main__":
    unittest.main()
