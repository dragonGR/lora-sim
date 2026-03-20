import unittest

from lora_sim.app.runner import run_scenario


class GatewayAndAckTests(unittest.TestCase):
    def test_gateway_capacity_scenario_uses_gateway_stats(self) -> None:
        metrics = run_scenario("scenarios/gateway_capacity.json")

        self.assertGreater(len(metrics.gateway_receptions), 0)
        self.assertGreater(metrics.uplinks_delivered, 0)

    def test_confirmed_uplink_tracks_ack_outcomes(self) -> None:
        metrics = run_scenario("scenarios/simple_link.json")

        self.assertEqual(metrics.ack_requests, metrics.packets_sent)
        self.assertEqual(metrics.ack_successes, metrics.packets_delivered)
        self.assertEqual(metrics.ack_failures, 0)
        self.assertLessEqual(metrics.ack_successes, metrics.ack_requests)


if __name__ == "__main__":
    unittest.main()
