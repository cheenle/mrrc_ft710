import unittest

from radio_state import RadioState
from scope_handler import ScopeHandler, WF_SIZE


class ScopeHandlerFallbackTests(unittest.TestCase):
    def test_smeter_fallback_generates_full_width_spectrum(self):
        state = RadioState(vfo_a_freq=14_200_000, s_meter=120, mode=2, preamp=1, attenuator=0)
        scope = ScopeHandler()

        scope.update_from_radio_state(state)

        self.assertEqual(len(scope.spectrum_rx1), WF_SIZE)
        self.assertEqual(len(scope.spectrum_rx2), WF_SIZE)
        self.assertEqual(scope.vfoa_freq, 14_200_000)
        self.assertEqual(scope.s_meter, 120)
        self.assertGreater(max(scope.spectrum_rx1), min(scope.spectrum_rx1))
        self.assertGreater(scope.last_update, 0)


if __name__ == "__main__":
    unittest.main()
