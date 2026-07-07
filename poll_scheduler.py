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
    POLL_IF_INTERVAL, POLL_VFO_INTERVAL, POLL_TX_STATUS_INTERVAL, POLL_TX_METERS_INTERVAL,
    POLL_SETTINGS_INTERVAL, POLL_SLOW_INTERVAL, POLL_TIMEOUT,
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
        # Timestamp of the last user-initiated command; pollers pause briefly
        # so the user's next command doesn't queue behind a poll cycle.
        self._last_user_command: float = 0.0
        # How long (seconds) to pause background polling after a user command.
        self._user_command_pause: float = 0.3

    async def start(self):
        """Launch all background polling tasks."""
        self._running = True
        self._tasks = [
            asyncio.create_task(self._poll_if(), name="poll_if"),
            asyncio.create_task(self._poll_vfo(), name="poll_vfo"),
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

    def note_user_command(self):
        """Record that a user-initiated command was just sent.

        Called by server.py after every UI-triggered set command.
        Causes poll loops to briefly pause so the user's next command
        isn't stuck behind a queued poll cycle on the serial lock.
        """
        import time
        self._last_user_command = time.time()

    async def _polling_paused(self) -> bool:
        """Return True if background polling should yield for a user command.

        When the user is actively tuning or adjusting settings, each
        poll cycle sends 3+ serial commands (FA/MD0/SM0).  If a user
        command arrives during that cycle, it waits behind all of them.
        By pausing briefly after each user command, the next user command
        can grab the serial lock immediately.
        """
        import time
        return time.time() < self._last_user_command + self._user_command_pause

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
        _loop_count = 0
        _last_logged_freq = None
        while self._running:
            try:
                if await self._polling_paused():
                    await asyncio.sleep(0.05)
                    continue
                if self.cat.connected:
                    changes = {}
                    if not await self._should_skip("if"):
                        # 3 queries only (FA/MD0/SM0) to keep this cycle
                        # short (~120 ms) so PTT/sets aren't blocked on the
                        # serial lock.  VS (active VFO) and FB (VFO-B freq)
                        # change rarely and are polled at 0.5 s in _poll_vfo.
                        # Inter-query pause checks let a user command preempt
                        # after the in-flight query (~40 ms).
                        if not await self._polling_paused():
                            freq = await self.cat.get_frequency("A", timeout=POLL_TIMEOUT)
                            if freq is not None and 30000 <= freq <= 75000000:
                                changes["vfo_a_freq"] = freq
                                if (freq != _last_logged_freq
                                        or _loop_count % 100 == 0):
                                    _delta = ""
                                    if _last_logged_freq is not None:
                                        _delta = f" ({freq - _last_logged_freq:+d} Hz)"
                                    logger.info(
                                        "IF poll: vfo_a=%d Hz%s (loop=%d)",
                                        freq, _delta, _loop_count)
                                    _last_logged_freq = freq
                        if not await self._polling_paused():
                            mode = await self.cat.get_mode(timeout=POLL_TIMEOUT)
                            if mode is not None:
                                changes["mode"] = mode
                        if not await self._polling_paused():
                            sm = await self.cat.get_s_meter(timeout=POLL_TIMEOUT)
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

            _loop_count += 1
            await asyncio.sleep(POLL_IF_INTERVAL)

    # ── Tier 1b: Active VFO + VFO-B freq (medium cadence) ──────────

    async def _poll_vfo(self):
        """Poll VS (active VFO) and FB (VFO-B freq) at medium cadence.

        These change rarely (only on user VFO switch / VFO-B tuning) so
        they don't need the 0.1 s fast-poll cadence — keeping them out
        of _poll_if shortens the fast cycle and keeps PTT/sets snappy.
        """
        while self._running:
            try:
                if await self._polling_paused():
                    await asyncio.sleep(0.05)
                    continue
                if self.cat.connected and not await self._should_skip("vfo"):
                    changes = {}
                    active = await self.cat.get_active_vfo(timeout=POLL_TIMEOUT)
                    if active is not None:
                        changes["active_vfo"] = active
                    if not await self._polling_paused():
                        freq_b = await self.cat.get_frequency("B", timeout=POLL_TIMEOUT)
                        if freq_b is not None and 30000 <= freq_b <= 75000000:
                            changes["vfo_b_freq"] = freq_b
                    if changes:
                        changed = self.state.update(**changes)
                        if changed and self._on_state_changed:
                            await self._on_state_changed()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug("VFO poll error: %s", e)
            await asyncio.sleep(POLL_VFO_INTERVAL)

    # ── Tier 2B: TX status ────────────────────────────────────────

    async def _poll_tx_status(self):
        """Poll TX; at medium frequency to detect radio-originated PTT changes."""
        failures = 0
        while self._running:
            try:
                if await self._polling_paused():
                    await asyncio.sleep(0.05)
                    continue
                if self.cat.connected and not await self._should_skip("tx_status"):
                    ptt = await self.cat.get_ptt(timeout=POLL_TIMEOUT)
                    if ptt is not None:
                        was_tx = self.state.tx_status > 0
                        changed = self.state.update(tx_status=ptt)
                        # Reset TX-only meters to zero when transitioning to RX,
                        # otherwise they keep the last TX reading forever
                        # (the TX-meters poller only runs during transmit).
                        if ptt == 0 and was_tx:
                            changed |= self.state.update(
                                power_meter=0, alc_meter=0,
                                swr_meter=0, comp_meter=0)
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
                if await self._polling_paused():
                    await asyncio.sleep(0.05)
                    continue
                if self.cat.connected and self.state.is_transmitting:
                    changes = {}
                    if not await self._should_skip("alc_meter"):
                        v = await self.cat.get_meter("RM4", timeout=POLL_TIMEOUT)
                        if v is not None:
                            changes["alc_meter"] = v
                    if not await self._should_skip("power_meter"):
                        v = await self.cat.get_meter("RM5", timeout=POLL_TIMEOUT)
                        if v is not None:
                            changes["power_meter"] = v
                    if not await self._should_skip("swr_meter"):
                        v = await self.cat.get_meter("RM6", timeout=POLL_TIMEOUT)
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
            # AC returns P1P2P3 (e.g. "010"=ATU on). Map to state: 0=off, 1=on, 2=tuning
            ("tuner_status", "AC", lambda r: (
                2 if len(r) > 4 and r[4] == '1' else  # P3==1 → tuning
                1 if len(r) > 3 and r[3] == '1' else  # P2==1 → on
                0  # P2==0 → off
            ) if r and len(r) > 2 else None),
            ("scope_on", "SS01", lambda r: int(r[4:]) == 1 if r and len(r) >= 5 else None),
            ("antenna", "AN", lambda r: int(r[2:]) if r and len(r) >= 3 else None),
            ("agc", "GT", lambda r: int(r[2:]) if r and len(r) >= 4 else None),
            # DO NOT poll "DN" — on the FT-710, "DN;" is NOT a DNR query;
            # it is the "step active VFO DOWN one tuning step" command (~20 Hz).
            # Polling it every 2 s was slowly walking the active VFO frequency
            # downward.  DNR level is not polled (the DN command is unsafe).
        ]

        while self._running:
            try:
                if await self._polling_paused():
                    await asyncio.sleep(0.05)
                    continue
                if self.cat.connected:
                    changes = {}
                    for field, cmd, parser in fields_to_poll:
                        # Yield between queries if a user command (PTT, tune,
                        # etc.) is pending — otherwise this 13-query cycle
                        # holds the serial lock for ~500 ms and stalls PTT.
                        if await self._polling_paused():
                            break
                        if await self._should_skip(field):
                            continue
                        resp = await self.cat.query(cmd, timeout=POLL_TIMEOUT)
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
                if await self._polling_paused():
                    await asyncio.sleep(0.05)
                    continue
                if self.cat.connected:
                    changes = {}
                    if not await self._should_skip("id_meter"):
                        v = await self.cat.get_meter("RM7", timeout=POLL_TIMEOUT)
                        if v is not None:
                            changes["id_meter"] = v
                    if not await self._should_skip("vd_meter"):
                        v = await self.cat.get_meter("RM8", timeout=POLL_TIMEOUT)
                        if v is not None:
                            changes["vd_meter"] = v
                    if not await self._should_skip("compressor"):
                        resp = await self.cat.query("PR", timeout=POLL_TIMEOUT)
                        if resp and isinstance(resp, str):
                            changes["compressor"] = resp.endswith("1")
                    if not await self._should_skip("contour_level"):
                        resp = await self.cat.query("CO", timeout=POLL_TIMEOUT)
                        if resp and len(resp) >= 5:
                            try:
                                v = int(resp[2:5])
                                if v is not None:
                                    changes["contour_level"] = v
                            except ValueError:
                                pass
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
