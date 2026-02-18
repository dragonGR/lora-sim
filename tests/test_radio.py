import unittest

from lora_sim.domain.radio import RadioConfig


class RadioTests(unittest.TestCase):
    def test_airtime_grows_with_payload(self) -> None:
        radio = RadioConfig(spreading_factor=9)

        small = radio.airtime_seconds(12)
        large = radio.airtime_seconds(32)

        self.assertGreater(small, 0)
        self.assertGreater(large, small)


if __name__ == "__main__":
    unittest.main()
