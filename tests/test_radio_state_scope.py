import unittest

from radio_state import RadioState


class RadioStateScopeTests(unittest.TestCase):
    def test_scope_fields_are_serialized_and_dirty(self):
        state = RadioState()

        changed = state.update(scope_span=7, scope_mode=3, scope_start_freq=14_150_000)
        dirty = state.to_dirty_dict(changed)

        self.assertEqual(dirty["scope_span"], 7)
        self.assertEqual(dirty["scope_mode"], 3)
        self.assertEqual(dirty["scope_start_freq"], 14_150_000)
        self.assertEqual(state.to_dict()["scope_span"], 7)


if __name__ == "__main__":
    unittest.main()
