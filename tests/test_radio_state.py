"""
Tests for RadioState — SDD §7.2, §9.7 (AD-003 dirty-field broadcasting).
Verifies: field mutation, dirty tracking, derived properties,
serialization, from_sync_result deserialization.
"""
import unittest

from radio_state import RadioState
from config import MODE_NUM_TO_NAME, MODE_DISPLAY_NAMES


class RadioStateFieldMutationTests(unittest.TestCase):
    """SDD AD-003: Dirty-field tracking for efficient partial broadcasts."""

    def setUp(self):
        self.state = RadioState()

    def test_initial_state_has_defaults(self):
        self.assertEqual(self.state.vfo_a_freq, 14_200_000)
        self.assertEqual(self.state.vfo_b_freq, 7_050_000)
        self.assertEqual(self.state.active_vfo, "A")
        self.assertEqual(self.state.tx_status, 0)
        self.assertEqual(self.state.af_gain, 128)
        self.assertEqual(self.state.rf_gain, 255)
        self.assertEqual(self.state.rf_power, 100)
        self.assertFalse(self.state.serial_connected)
        self.assertFalse(self.state.is_transmitting)

    def test_update_returns_changed_fields_only(self):
        changed = self.state.update(vfo_a_freq=14_250_000, mode=2)
        self.assertEqual(changed, {"vfo_a_freq", "mode"})

    def test_update_ignores_unchanged_values(self):
        changed = self.state.update(vfo_a_freq=14_200_000)  # Same as default
        self.assertEqual(changed, set())

    def test_update_ignores_unknown_fields(self):
        changed = self.state.update(nonexistent_field=42)
        self.assertEqual(changed, set())

    def test_dirty_fields_accumulate_across_updates(self):
        self.state.update(vfo_a_freq=14_250_000)
        self.state.update(mode=3)
        dirty = self.state.get_and_clear_dirty()
        self.assertEqual(dirty, {"vfo_a_freq", "mode"})
        # After clear, dirty set is empty
        self.assertEqual(self.state.get_and_clear_dirty(), set())

    def test_mark_dirty_explicitly(self):
        self.state.mark_dirty("s_meter", "tx_status")
        dirty = self.state.get_and_clear_dirty()
        self.assertIn("s_meter", dirty)
        self.assertIn("tx_status", dirty)

    def test_last_update_changes_on_mutation(self):
        self.assertAlmostEqual(self.state.last_update, 0.0)
        self.state.update(vfo_a_freq=14_250_000)
        self.assertGreater(self.state.last_update, 0)

    def test_multiple_fields_batched_update(self):
        changed = self.state.update(
            vfo_a_freq=14_250_000,
            mode=2,
            s_meter=150,
            preamp=1,
        )
        self.assertEqual(len(changed), 4)
        self.assertEqual(self.state.vfo_a_freq, 14_250_000)
        self.assertEqual(self.state.mode, 2)
        self.assertEqual(self.state.s_meter, 150)
        self.assertEqual(self.state.preamp, 1)


class RadioStateDerivedPropertiesTests(unittest.TestCase):
    """SDD §7.2: Derived properties (mode_name, s_unit, band_name, etc.)."""

    def setUp(self):
        self.state = RadioState()

    def test_active_freq_returns_vfo_a_when_a_active(self):
        self.state.active_vfo = "A"
        self.state.vfo_a_freq = 14_200_000
        self.assertEqual(self.state.active_freq, 14_200_000)

    def test_active_freq_returns_vfo_b_when_b_active(self):
        self.state.active_vfo = "B"
        self.state.vfo_b_freq = 7_050_000
        self.assertEqual(self.state.active_freq, 7_050_000)

    def test_mode_name_lookup(self):
        self.state.mode = 1
        self.assertEqual(self.state.mode_name, "LSB")
        self.state.mode = 2
        self.assertEqual(self.state.mode_name, "USB")

    def test_mode_display(self):
        self.state.mode = 2
        display = self.state.mode_display
        self.assertIsInstance(display, str)
        self.assertGreater(len(display), 0)

    def test_band_name_for_known_band(self):
        self.state.vfo_a_freq = 14_200_000
        self.state.active_vfo = "A"
        self.assertEqual(self.state.band_name, "20m")

    def test_band_name_for_edge_case(self):
        self.state.vfo_a_freq = 7_050_000
        self.state.active_vfo = "A"
        self.assertEqual(self.state.band_name, "40m")

    def test_is_transmitting_during_tx(self):
        self.state.tx_status = 1
        self.assertTrue(self.state.is_transmitting)

    def test_is_transmitting_during_tune(self):
        self.state.tx_status = 2
        self.assertTrue(self.state.is_transmitting)

    def test_is_not_transmitting_in_rx(self):
        self.state.tx_status = 0
        self.assertFalse(self.state.is_transmitting)

    def test_s_meter_dbm_is_numeric(self):
        self.state.s_meter = 150
        dbm = self.state.s_meter_dbm
        self.assertIsInstance(dbm, float)

    def test_s_unit_is_string(self):
        self.state.s_meter = 120
        s_unit = self.state.s_unit
        self.assertIsInstance(s_unit, str)
        self.assertTrue(s_unit.startswith("S") or s_unit == "S0")

    def test_preamp_label(self):
        self.state.preamp = 0
        self.assertEqual(self.state.preamp_label, "OFF")
        self.state.preamp = 1
        self.assertEqual(self.state.preamp_label, "AMP1")
        self.state.preamp = 2
        self.assertEqual(self.state.preamp_label, "AMP2")

    def test_attenuator_label(self):
        for i in range(4):
            self.state.attenuator = i
            self.assertIsInstance(self.state.attenuator_label, str)


class RadioStateSerializationTests(unittest.TestCase):
    """SDD §9.7: to_dict / to_dirty_dict serialization for WS broadcast."""

    def setUp(self):
        self.state = RadioState()

    def test_to_dict_includes_all_core_fields(self):
        d = self.state.to_dict(include_derived=False)
        self.assertIn("vfo_a_freq", d)
        self.assertIn("vfo_b_freq", d)
        self.assertIn("mode", d)
        self.assertIn("tx_status", d)
        self.assertIn("s_meter", d)
        self.assertIn("af_gain", d)
        self.assertIn("rf_power", d)
        self.assertIn("filter_width", d)
        self.assertIn("preamp", d)
        self.assertIn("noise_blanker", d)
        self.assertIn("scope_span", d)
        self.assertIn("serial_connected", d)

    def test_to_dict_includes_derived_fields_when_requested(self):
        d = self.state.to_dict(include_derived=True)
        self.assertIn("mode_name", d)
        self.assertIn("band_name", d)
        self.assertIn("s_unit", d)
        self.assertIn("is_transmitting", d)
        self.assertIn("filter_hz", d)

    def test_to_dirty_dict_only_returns_requested_fields(self):
        self.state.update(vfo_a_freq=14_250_000, mode=2, s_meter=100)
        dirty = self.state.to_dirty_dict({"vfo_a_freq", "s_meter"})
        self.assertEqual(set(dirty.keys()), {"vfo_a_freq", "s_meter"})
        self.assertEqual(dirty["vfo_a_freq"], 14_250_000)
        self.assertEqual(dirty["s_meter"], 100)

    def test_to_dirty_dict_ignores_unknown_fields(self):
        d = self.state.to_dirty_dict({"nonexistent"})
        self.assertEqual(d, {})

    def test_dict_values_match_object_attributes(self):
        self.state.vfo_a_freq = 14_250_000
        self.state.mode = 2
        d = self.state.to_dict(include_derived=False)
        self.assertEqual(d["vfo_a_freq"], 14_250_000)
        self.assertEqual(d["mode"], 2)
        self.assertEqual(d["active_vfo"], "A")
        self.assertEqual(d["active_freq"], 14_250_000)


class RadioStateFromSyncResultTests(unittest.TestCase):
    """SDD §9.6: CAT initial_state_sync → RadioState deserialization."""

    def test_from_sync_result_parses_known_fields(self):
        sync_data = {
            "vfo_a_freq": "FA014200000",
            "vfo_b_freq": "FB007050000",
            "mode": "MD02",
            "tx_status": "TX0",
            "s_meter": "SM00120",
            "filter_width": "SH005",
            "power_on": "PS1",
        }
        state = RadioState.from_sync_result(sync_data)
        self.assertEqual(state.vfo_a_freq, 14_200_000)
        self.assertEqual(state.vfo_b_freq, 7_050_000)
        self.assertEqual(state.mode, 2)
        self.assertEqual(state.tx_status, 0)
        self.assertEqual(state.s_meter, 120)
        self.assertEqual(state.filter_width, 5)
        self.assertTrue(state.power_on)

    def test_from_sync_result_handles_empty_data(self):
        state = RadioState.from_sync_result({})
        # Should return default state
        self.assertEqual(state.vfo_a_freq, 14_200_000)
        self.assertFalse(state.serial_connected)

    def test_from_sync_result_handles_malformed_responses(self):
        sync_data = {
            "vfo_a_freq": "FA",    # Too short — len <= 2, parser returns 0
            "mode": "MD",           # Too short
            "s_meter": "SM",        # Too short
        }
        state = RadioState.from_sync_result(sync_data)
        # Should not crash; for short strings, parser returns 0 or default
        self.assertIsNotNone(state)
        self.assertEqual(state.mode, 1)  # Default preserved

    def test_from_sync_result_parses_boolean_fields(self):
        sync_data = {
            "noise_blanker": "NB01",
            "noise_reduction": "NR00",
            "auto_notch": "BC1",
        }
        state = RadioState.from_sync_result(sync_data)
        self.assertTrue(state.noise_blanker)
        self.assertFalse(state.noise_reduction)
        # BC command is BC0/BC1; BC ends with "1" → True
        self.assertTrue(state.auto_notch)

    def test_from_sync_result_parses_preamp_attenuator(self):
        sync_data = {
            "preamp": "PA02",
            "attenuator": "RA03",
        }
        state = RadioState.from_sync_result(sync_data)
        self.assertEqual(state.preamp, 2)
        self.assertEqual(state.attenuator, 3)

    def test_from_sync_result_parses_tuner(self):
        sync_data = {"tuner_status": "AC001"}
        state = RadioState.from_sync_result(sync_data)
        self.assertEqual(state.tuner_status, 1)


if __name__ == "__main__":
    unittest.main()
