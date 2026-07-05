"""
FT-710 Poll Scheduler
=====================
Background asyncio tasks that poll the radio at different rates.
Tiered polling: high-frequency for freq/mode/S-meter, medium for
TX status/meters, low for settings, very low for telemetry.

Also handles serial connection monitoring and auto-reconnect.
"""
import asyncio
import logging
from typing import Optional, Callable, Awaitable

from cat_controller import CatController
from radio_state import RadioState
from config import (
    POLL_IF_INTERVAL, POLL_TX_STATUS_INTERVAL, POLL_TX_METERS_INTERVAL,
    POLL_SETTINGS_INTERVAL, POLL_SLOW_INTERVAL,
)

logger = logging.getLogger("ft710.poll")


class PollScheduler:
    """Manages background polling tasks for the FT-710."""

    def __init__(
        self,
        cat: CatController,
        state: RadioState,
        on_state_changed: Optional[Callable[[], Awaitable[None]]] = None,
    ):
        self.cat = cat
        self.state = state
        self._on_state_changed = on_state_changed  # async callback for broadcasts
        self._tasks: list[asyncio.Task] = []
        self._running = False
        self._user_command_lock = asyncio.Lock()
        # Skip certain polls after a user set command to avoid echo
        self._skip_until: dict[str, float] = {}

    async def start(self):
        """Launch all background polling tasks."""
        self._running = True
        self._tasks = [
            asyncio.create_task(self._poll_if(), name="poll_if"),
            asyncio.create_task(self._poll_tx_status(), name="poll_tx"),
            asyncio.create_task(self._poll_tx_meters(), name="poll_tx_meters"),
            asyncio.create_task(self._poll_settings(), name="poll_settings"),
            asyncio.create_task(self._poll_slow(), name="poll_slow"),
            asyncio.create_task(self._connection_watchdog(), name="conn_watch"),
        ]
        logger.info("Poll scheduler started (%d tasks)", len(self._tasks))

    async def stop(self):
        """Cancel all polling tasks."""
        self._running = False
        for t in self._tasks:
            t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Poll scheduler stopped")

    def skip_next_poll(self, field: str, duration: float = 2.0):
        """Skip polling for a given field for `duration` seconds.

        Called after a user-initiated set command to avoid echoing
        the value back before the radio actually processes it.
        """
        import time
        self._skip_until[field] = time.time() + duration

    async def _should_skip(self, field: str) -> bool:
        import time
        until = self._skip_until.get(field, 0)
        return time.time() < until

    # ── Tier 1: High-frequency (freq + mode + S-meter via IF) ────

    async def _poll_if(self):
        """Poll freq+mode+S-meter at high frequency.

        Uses dedicated FA/MD0/SM0 commands instead of IF; because
        the FT-710's IF response format is binary/BCD and harder to
        parse reliably across firmware versions.
        """
        failures = 0
        while self._running:
            try:
                if self.cat.connected:
                    changes = {}
                    if not await self._should_skip("if"):
                        # Frequency
                        freq = await self.cat.get_frequency("A")
                        if freq is not None and 30000 <= freq <= 75000000:
                            changes["vfo_a_freq"] = freq
                        # Mode
                        mode = await self.cat.get_mode()
                        if mode is not None:
                            changes["mode"] = mode
                        # S-meter
                        sm = await self.cat.get_s_meter()
                        if sm is not None:
                            changes["s_meter"] = sm
                    if changes:
                        changed = self.state.update(**changes)
                        if changed and self._on_state_changed:
                            await self._on_state_changed()
                        failures = 0
                    else:
                        failures += 1
                else:
                    failures += 1
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug("IF poll error: %s", e)
                failures += 1

            if failures >= 5:
                self.state.update(serial_connected=False)
                if self._on_state_changed:
                    await self._on_state_changed()

            await asyncio.sleep(POLL_IF_INTERVAL)

    # ── Tier 2B: TX status ────────────────────────────────────────

    async def _poll_tx_status(self):
        """Poll TX; at medium frequency to detect radio-originated PTT changes."""
        failures = 0
        while self._running:
            try:
                if self.cat.connected and not await self._should_skip("tx_status"):
                    ptt = await self.cat.get_ptt()
                    if ptt is not None:
                        changed = self.state.update(tx_status=ptt)
                        if changed and self._on_state_changed:
                            await self._on_state_changed()
                        failures = 0
                    else:
                        failures += 1
                else:
                    failures += 1
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug("TX poll error: %s", e)
                failures += 1
            await asyncio.sleep(POLL_TX_STATUS_INTERVAL)

    # ── Tier 2A: TX meters (ALC, Power, SWR) — TX only ────────────

    async def _poll_tx_meters(self):
        """Poll RM4/RM5/RM6 during transmit.  Idle during RX."""
        while self._running:
            try:
                if self.cat.connected and self.state.is_transmitting:
                    changes = {}
                    if not await self._should_skip("alc_meter"):
                        v = await self.cat.get_meter("RM4")
                        if v is not None:
                            changes["alc_meter"] = v
                    if not await self._should_skip("power_meter"):
                        v = await self.cat.get_meter("RM5")
                        if v is not None:
                            changes["power_meter"] = v
                    if not await self._should_skip("swr_meter"):
                        v = await self.cat.get_meter("RM6")
                        if v is not None:
                            changes["swr_meter"] = v
                    if changes:
                        changed = self.state.update(**changes)
                        if changed and self._on_state_changed:
                            await self._on_state_changed()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug("TX meter poll error: %s", e)
            await asyncio.sleep(POLL_TX_METERS_INTERVAL)

    # ── Tier 3: Settings (filter, gains, preamp, att, NR, NB, AN, tuner) ──

    async def _poll_settings(self):
        """Poll slowly-changing radio settings."""
        fields_to_poll = [
            ("filter_width", "SH0", lambda r: int(r[3:]) if len(r) > 3 else None),
            ("af_gain", "AG0", lambda r: int(r[2:]) if len(r) > 2 else None),
            ("rf_power", "PC", lambda r: int(r[2:]) if len(r) > 2 else None),
            ("preamp", "PA0", lambda r: int(r[3:]) if len(r) > 3 else None),
            ("attenuator", "RA0", lambda r: int(r[3:]) if len(r) > 3 else None),
            ("noise_blanker", "NB0", lambda r: r.endswith("1") if r else False),
            ("noise_reduction", "NR0", lambda r: r.endswith("1") if r else False),
            ("auto_notch", "BC", lambda r: r.endswith("1") if r else False),
            ("tuner_status", "AC", lambda r: int(r[2:]) if len(r) > 2 else None),
        ]

        while self._running:
            try:
                if self.cat.connected:
                    changes = {}
                    for field, cmd, parser in fields_to_poll:
                        if await self._should_skip(field):
                            continue
                        resp = await self.cat.query(cmd)
                        if resp:
                            try:
                                value = parser(resp)
                                if value is not None:
                                    changes[field] = value
                            except (ValueError, IndexError):
                                pass
                    if changes:
                        changed = self.state.update(**changes)
                        if changed and self._on_state_changed:
                            await self._on_state_changed()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug("Settings poll error: %s", e)
            await asyncio.sleep(POLL_SETTINGS_INTERVAL)

    # ── Tier 4: Slow telemetry (drain current/voltage, compressor) ──

    async def _poll_slow(self):
        """Very slow poll for drain current, voltage, compressor state."""
        while self._running:
            try:
                if self.cat.connected:
                    changes = {}
                    if not await self._should_skip("id_meter"):
                        v = await self.cat.get_meter("RM7")
                        if v is not None:
                            changes["id_meter"] = v
                    if not await self._should_skip("vd_meter"):
                        v = await self.cat.get_meter("RM8")
                        if v is not None:
                            changes["vd_meter"] = v
                    if not await self._should_skip("compressor"):
                        resp = await self.cat.query("PR")
                        if resp and isinstance(resp, str):
                            changes["compressor"] = resp.endswith("1")
                    if changes:
                        changed = self.state.update(**changes)
                        if changed and self._on_state_changed:
                            await self._on_state_changed()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug("Slow poll error: %s", e)
            await asyncio.sleep(POLL_SLOW_INTERVAL)

    # ── Connection Watchdog ────────────────────────────────────────

    async def _connection_watchdog(self):
        """Monitor serial connection and attempt reconnection on failure."""
        while self._running:
            try:
                if not self.cat.connected:
                    self.state.update(serial_connected=False)
                    if self._on_state_changed:
                        await self._on_state_changed()
                    logger.warning("Serial disconnected, attempting reconnect...")
                    reconnected = await self.cat.reconnect_loop()
                    if reconnected:
                        # Perform full state sync after reconnect
                        logger.info("Reconnected! Performing state sync...")
                        sync_data = await self.cat.initial_state_sync()
                        new_state = RadioState.from_sync_result(sync_data)
                        new_state.serial_connected = True
                        # Copy all fields
                        for field_name in vars(new_state):
                            if not field_name.startswith('_'):
                                setattr(self.state, field_name, getattr(new_state, field_name))
                        self.state.mark_dirty(*list(vars(new_state).keys()))
                        if self._on_state_changed:
                            await self._on_state_changed()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error("Watchdog error: %s", e)
            await asyncio.sleep(1.0)
