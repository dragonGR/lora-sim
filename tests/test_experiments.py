import unittest

from lora_sim.simulation.experiments import compare_scenarios, sweep_scenario


class ExperimentTests(unittest.TestCase):
    def test_sweep_returns_multiple_points(self) -> None:
        results = sweep_scenario(
            "scenarios/simple_link.json",
            parameter_path="nodes.gateway.x_m",
            start=500,
            stop=1500,
            step=500,
            seed=42,
        )

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["value"], 500)
        self.assertEqual(results[-1]["value"], 1500)

    def test_compare_scenarios_uses_same_seed(self) -> None:
        left, right = compare_scenarios(
            "scenarios/simple_link.json",
            "scenarios/multi_node_collision.json",
            seed=99,
        )

        self.assertEqual(left.seed, 99)
        self.assertEqual(right.seed, 99)


if __name__ == "__main__":
    unittest.main()
