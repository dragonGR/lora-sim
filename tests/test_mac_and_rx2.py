import unittest

from lora_sim.app.runner import run_scenario


class MacAndRx2Tests(unittest.TestCase):
    def test_duty_cycle_constraints_create_wait_time(self) -> None:
        metrics = run_scenario("scenarios/duty_cycle_rx2.json")

        self.assertGreater(metrics.duty_cycle_delays, 0)
        self.assertGreater(metrics.total_duty_cycle_wait_seconds, 0.0)

    def test_rx2_fallback_is_used_when_rx1_fails(self) -> None:
        metrics = run_scenario("scenarios/duty_cycle_rx2.json")

        self.assertGreater(metrics.ack_successes, 0)
        self.assertGreater(metrics.rx2_successes, 0)


if __name__ == "__main__":
    unittest.main()
