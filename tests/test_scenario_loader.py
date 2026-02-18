import unittest

from lora_sim.simulation.scenario import load_scenario


class ScenarioLoaderTests(unittest.TestCase):
    def test_load_scenario_builds_nodes(self) -> None:
        scenario = load_scenario("scenarios/simple_link.json")

        self.assertEqual(scenario.name, "Simple link baseline")
        self.assertEqual(len(scenario.nodes), 2)
        self.assertIsNotNone(scenario.node_map()["sensor-a"].traffic)


if __name__ == "__main__":
    unittest.main()
