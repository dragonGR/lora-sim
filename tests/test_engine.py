import unittest

from lora_sim.app.runner import run_scenario


class EngineTests(unittest.TestCase):
    def test_baseline_scenario_is_deterministic(self) -> None:
        first = run_scenario("scenarios/simple_link.json")
        second = run_scenario("scenarios/simple_link.json")

        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.packets_sent, 8)
        self.assertEqual(first.packets_delivered, 8)

    def test_collision_scenario_produces_losses(self) -> None:
        metrics = run_scenario("scenarios/multi_node_collision.json")

        self.assertGreaterEqual(metrics.packets_sent, 12)
        self.assertGreater(metrics.collisions, 0)
        self.assertGreater(metrics.packets_lost, 0)
        self.assertGreater(metrics.total_energy_joules, 0.0)


if __name__ == "__main__":
    unittest.main()
