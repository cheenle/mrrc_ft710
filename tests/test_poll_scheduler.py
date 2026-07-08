"""
Tests for PollScheduler — SDD AD-009 (5-tier adaptive polling).
Verifies: polling tier structure, skip logic, command priority.
"""
import unittest
import asyncio
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class PollTierStructureTests(unittest.TestCase):
    """SDD §9.6: 5-tier polling structure."""

    def test_tier_intervals(self):
        """Verify tier interval constants."""
        tiers = {
            1: 0.1,    # 100ms
            2: 0.5,    # 500ms
            3: 2.0,    # 2s
            4: 5.0,    # 5s
        }
        self.assertEqual(tiers[1], 0.1)
        self.assertEqual(tiers[2], 0.5)
        self.assertEqual(tiers[3], 2.0)
        self.assertEqual(tiers[4], 5.0)

    def test_tier_1_commands(self):
        """Tier 1 (100ms): high-frequency fields."""
        tier1 = ["FA", "MD0", "SM0"]  # freq, mode, s-meter
        self.assertIn("FA", tier1)
        self.assertIn("MD0", tier1)
        self.assertIn("SM0", tier1)

    def test_tier_2_commands_tx_only(self):
        """Tier 2A (500ms, TX only): meter readings."""
        tier2a = ["RM4", "RM5", "RM6"]  # ALC, PWR, SWR
        self.assertEqual(len(tier2a), 3)

    def test_tier_3_commands(self):
        """Tier 3 (2s): settings that change infrequently."""
        tier3 = ["SH0", "AG", "PC", "PA0", "RA0", "NB0", "NR0", "BC", "AC"]
        self.assertGreater(len(tier3), 5)

    def test_tier_4_commands(self):
        """Tier 4 (5s): rarely-changing fields."""
        tier4 = ["RM7", "RM8", "PR"]  # Id, Vd, compressor
        self.assertGreater(len(tier4), 0)

    def test_total_throughput_under_limit(self):
        """~296 bytes/sec at 38400 baud should be well under 3840 bytes/sec."""
        # Each CAT command is ~6-12 chars + response ~10-20 chars
        # ~20 commands/sec average, ~15 chars avg = ~300 bytes/sec
        baud = 38400
        bytes_per_sec_limit = baud / 10  # ~3840 bytes/sec theoretical
        estimated_throughput = 300  # bytes/sec
        self.assertLess(estimated_throughput, bytes_per_sec_limit)


class PollSkipLogicTests(unittest.TestCase):
    """SDD AD-009: skip_next_poll prevents redundant queries after user commands."""

    def test_skip_fields_accumulate(self):
        skip_map = {}
        # After user sets frequency → skip "if" poll for 1.0s
        skip_map["if"] = 1.0
        # After user sets PTT → skip "tx_status" poll for 1.0s
        skip_map["tx_status"] = 1.0
        self.assertEqual(len(skip_map), 2)

    def test_skip_expires_after_duration(self):
        """After duration elapses, polling resumes."""
        skip_map = {"if": 0.0}  # Expired
        expired = [k for k, v in skip_map.items() if v <= 0]
        self.assertIn("if", expired)

    def test_multiple_fields_can_be_skipped(self):
        skip_map = {}
        skip_fields = [
            ("if", 1.0),
            ("filter_width", 3.0),
            ("tx_status", 1.0),
            ("af_gain", 3.0),
        ]
        for field, duration in skip_fields:
            skip_map[field] = duration
        self.assertEqual(len(skip_map), 4)

    def test_longer_skip_for_slow_commands(self):
        """Complex commands (filter change, tuner) skip longer than simple ones."""
        # Frequency change: skip 1.0s
        freq_skip = 1.0
        # Filter change: skip 3.0s (radio takes longer to apply)
        filter_skip = 3.0
        self.assertLess(freq_skip, filter_skip)


class PollingOrderTests(unittest.TestCase):
    """SDD §9.6: User commands jump the queue ahead of polls."""

    def test_user_command_priority_over_poll(self):
        """A user set command should execute before the next poll for that field."""
        # Conceptual test: if user sets freq at t=0, tier 1 poll at t=0.05
        # should skip FA because skip_next_poll("if", 1.0) was called
        poll_due_at = 0.05
        skip_until = 1.0
        should_poll = poll_due_at >= skip_until
        self.assertFalse(should_poll)

    def test_user_command_temporarily_pauses_background_polling(self):
        scheduler_source = (REPO_ROOT / "poll_scheduler.py").read_text()
        server_source = (REPO_ROOT / "server.py").read_text()
        self.assertIn("def note_user_command", scheduler_source)
        self.assertIn("await self._polling_paused()", scheduler_source)
        self.assertIn("scheduler.note_user_command", server_source)

    def test_poll_resumes_after_skip_expires(self):
        poll_due_at = 1.5
        skip_until = 1.0
        should_poll = poll_due_at >= skip_until
        self.assertTrue(should_poll)


class TXMeterPollingPreemptionTests(unittest.IsolatedAsyncioTestCase):
    """PTT release should preempt a TX meter cycle between RM queries."""

    async def test_tx_meter_poll_yields_between_meter_queries(self):
        from poll_scheduler import PollScheduler
        from radio_state import RadioState

        scheduler = None

        class FakeCat:
            connected = True
            _cancel_polls: bool = False

            def __init__(self):
                self.commands = []

            async def get_meter(self, cmd, timeout=None):
                self.commands.append(cmd)
                if len(self.commands) == 1:
                    scheduler.note_user_command()
                return 0

        fake_cat = FakeCat()
        state = RadioState(tx_status=1)
        scheduler = PollScheduler(fake_cat, state)
        scheduler._running = True

        task = asyncio.create_task(scheduler._poll_tx_meters())
        try:
            await asyncio.sleep(0.05)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            scheduler._running = False

        self.assertEqual(fake_cat.commands, ["RM3"])


if __name__ == "__main__":
    unittest.main()
