"""
FT-710 Serial CAT Protocol Controller
=====================================
Manages the serial connection to the FT-710, formats CAT commands,
and parses responses.  All serial access is serialized through an
asyncio.Lock to prevent interleaved reads/writes.

Uses standard pyserial (synchronous) with asyncio.to_thread()
for I/O — no serial_asyncio dependency needed.
"""
import asyncio
import logging
import time
from typing import Optional

import serial
import serial.tools.list_ports

from config import SERIAL_TIMEOUT, RECONNECT_BASE_DELAY, RECONNECT_MAX_DELAY

logger = logging.getLogger("ft710.cat")


class CatController:
    """Asynchronous serial CAT protocol handler for Yaesu FT-710.

    Uses pyserial (sync API) under the hood; all blocking I/O is
    offloaded to a thread pool via asyncio.to_thread().
    """

    def __init__(self, port: str, baudrate: int = 38400):
        self.port = port
        self.baudrate = baudrate
        self._ser: Optional[serial.Serial] = None
        self._lock = asyncio.Lock()
        self._timeout = SERIAL_TIMEOUT
        self._connected = False
        self._model = "Unknown"

    # ── Connection Management ──────────────────────────────────────

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def model(self) -> str:
        return self._model

    async def connect(self) -> bool:
        """Open the serial port and verify the radio responds.

        Returns True if connection and radio verification succeeded.
        """
        try:
            logger.info("Opening serial port %s at %d baud", self.port, self.baudrate)

            def _open():
                s = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=0.1,        # Short timeout for reads
                    write_timeout=1.0,
                    xonxoff=False,
                    rtscts=False,
                )
                return s

            self._ser = await asyncio.to_thread(_open)

            # Flush any stale data
            await asyncio.sleep(0.5)
            await asyncio.to_thread(self._ser.reset_input_buffer)

            # Verify the radio responds
            resp = await self.query("ID")
            if resp is not None and "ID" in resp:
                self._connected = True
                model_id = resp[2:] if len(resp) >= 6 else resp
                self._model = model_id
                logger.info("Connected to FT-710 (ID=%s) on %s", model_id, self.port)
            else:
                logger.warning("No ID response from radio on %s. Check connection.", self.port)
                self._connected = True  # Mark connected anyway; UI still works
            return self._connected
        except Exception as e:
            logger.error("Failed to connect to %s: %s", self.port, e)
            await self._cleanup()
            return False

    async def disconnect(self):
        """Close the serial port."""
        logger.info("Disconnecting from %s", self.port)
        self._connected = False
        await self._cleanup()

    async def _cleanup(self):
        if self._ser is not None:
            try:
                await asyncio.to_thread(self._ser.close)
            except Exception:
                pass
            self._ser = None

    # ── Low-level I/O ─────────────────────────────────────────────

    async def _write(self, data: bytes):
        """Write bytes to the serial port (threaded)."""
        if self._ser is None or not self._ser.is_open:
            raise serial.SerialException("Port not open")

        def _w():
            self._ser.reset_input_buffer()  # Clear stale input
            self._ser.write(data)
            self._ser.flush()

        await asyncio.to_thread(_w)

    async def _read_until(self, terminator: bytes = b";") -> bytes:
        """Read bytes from serial port until terminator or timeout."""
        if self._ser is None or not self._ser.is_open:
            raise serial.SerialException("Port not open")

        def _r():
            buf = bytearray()
            deadline = time.monotonic() + self._timeout
            while time.monotonic() < deadline:
                waiting = self._ser.in_waiting
                if waiting > 0:
                    chunk = self._ser.read(waiting)
                    buf.extend(chunk)
                    if terminator in buf:
                        # Return everything up to and including the terminator
                        idx = buf.find(terminator)
                        return bytes(buf[:idx + len(terminator)])
                # Only sleep if no data was waiting
                time.sleep(0.01)
            # Timeout — return whatever we have
            return bytes(buf) if buf else None

        return await asyncio.to_thread(_r)

    # ── Command Interface ──────────────────────────────────────────

    async def send_command(self, cmd: str) -> Optional[str]:
        """Send a CAT command and return the response.

        All serial I/O is serialized through self._lock.
        Returns the response string (without trailing ';') or None on timeout/error.

        Args:
            cmd: CAT command string WITHOUT trailing ';' (it's appended here).
        """
        async with self._lock:
            if not self._connected or self._ser is None:
                return None

            raw = (cmd + ";").encode("ascii")
            try:
                await self._write(raw)
            except Exception as e:
                logger.error("Serial write error for '%s': %s", cmd, e)
                self._connected = False
                return None

            # Read response
            try:
                response_bytes = await self._read_until(b";")
                if response_bytes is None:
                    logger.debug("Command timeout (no data): %s", cmd)
                    return None
                if not response_bytes:
                    logger.debug("Command timeout (empty): %s", cmd)
                    return None
                return response_bytes.decode("ascii", errors="replace").rstrip(";")
            except Exception as e:
                logger.error("Serial read error for '%s': %s", cmd, e)
                self._connected = False
                return None

    async def query(self, cmd: str) -> Optional[str]:
        """Send a query command (no value, just prefix + ';').

        Example: query("FA") -> "FA014200000"
        """
        return await self.send_command(cmd)

    async def set(self, cmd: str) -> bool:
        """Send a set command (prefix + value + ';').

        Returns True if no ? error response was received.

        Example: set("FA014200000") -> True
        """
        resp = await self.send_command(cmd)
        if resp is not None and "?" in resp:
            logger.warning("CAT error response for '%s': %s", cmd, resp)
            return False
        return True

    # ── High-Level Command Helpers ─────────────────────────────────

    async def set_frequency(self, freq_hz: int, vfo: str = "A") -> bool:
        prefix = "FA" if vfo.upper() == "A" else "FB"
        return await self.set(f"{prefix}{freq_hz:09d}")

    async def get_frequency(self, vfo: str = "A") -> Optional[int]:
        prefix = "FA" if vfo.upper() == "A" else "FB"
        resp = await self.query(prefix)
        if resp and len(resp) >= len(prefix) + 1:
            try:
                return int(resp[len(prefix):])
            except ValueError:
                return None
        return None

    async def set_mode(self, mode_num: int) -> bool:
        return await self.set(f"MD0{mode_num:X}")

    async def get_mode(self) -> Optional[int]:
        resp = await self.query("MD0")
        if resp and len(resp) >= 4:
            try:
                return int(resp[3:], 16)
            except ValueError:
                return None
        return None

    async def set_ptt(self, tx: bool) -> bool:
        return await self.set("TX1" if tx else "TX0")

    async def set_tune(self, tune: bool) -> bool:
        return await self.set("TX2" if tune else "TX0")

    async def get_ptt(self) -> Optional[int]:
        resp = await self.query("TX")
        if resp and len(resp) >= 3:
            try:
                return int(resp[2:])
            except ValueError:
                return None
        return None

    async def get_s_meter(self) -> Optional[int]:
        resp = await self.query("SM0")
        if resp and len(resp) >= 4:
            try:
                return int(resp[3:])
            except ValueError:
                return None
        return None

    async def get_info(self) -> Optional[dict]:
        """Get combined info via IF; command."""
        resp = await self.query("IF")
        if not resp or len(resp) < 10:
            return None
        try:
            # Parse: IF + freq(9 digits or space-padded) + status + S-meter
            tail = resp[2:]  # Skip "IF"
            freq_part = ''
            i = 0
            # Frequency digits (may be space-padded)
            while i < len(tail) and (tail[i].isdigit() or tail[i] == ' '):
                freq_part += tail[i]
                i += 1
            freq_str = freq_part.strip()
            # FT-710 IF returns Hz directly (9 digits), NOT tens-of-Hz.
            # Older Yaesu models use 11-digit tens-of-Hz; FT-710 uses 9-digit Hz.
            freq_hz = int(freq_str) if freq_str else None

            # After frequency: mode byte + misc
            rest = tail[i:]
            mode_num = None
            if len(rest) > 0 and rest[0].isdigit():
                mode_num = int(rest[0], 16) if rest[0] in '0123456789ABCDEFabcdef' else None

            # S-meter: find 3 consecutive digits near the end
            smeter = None
            digits = ''.join(c for c in rest if c.isdigit())
            if len(digits) >= 3:
                smeter = int(digits[-3:])

            result = {}
            if freq_hz is not None:
                result["freq"] = freq_hz
            if mode_num is not None:
                result["mode"] = mode_num
            if smeter is not None:
                result["s_meter"] = smeter
            return result if result else None
        except (ValueError, IndexError) as e:
            logger.debug("IF parse error: %s (raw: %s)", e, resp)
            return None

    async def get_meter(self, meter: str) -> Optional[int]:
        resp = await self.query(meter)
        if resp and len(resp) >= 4:
            try:
                return int(resp[4:])
            except ValueError:
                return None
        return None

    async def set_filter_width(self, index: int) -> bool:
        return await self.set(f"SH0{index:02d}")

    async def get_filter_width(self) -> Optional[int]:
        resp = await self.query("SH0")
        if resp and len(resp) >= 5:
            try:
                return int(resp[3:5])
            except ValueError:
                try:
                    return int(resp[3])
                except ValueError:
                    return None
        return None

    async def set_af_gain(self, value: int) -> bool:
        return await self.set(f"AG0{value:03d}")

    async def set_rf_gain(self, value: int) -> bool:
        return await self.set(f"RG0{value:03d}")

    async def set_rf_power(self, value: int) -> bool:
        return await self.set(f"PC{value:03d}")

    async def set_preamp(self, value: int) -> bool:
        return await self.set(f"PA0{value}")

    async def set_attenuator(self, value: int) -> bool:
        return await self.set(f"RA0{value}")

    async def set_noise_blanker(self, on: bool) -> bool:
        return await self.set(f"NB0{1 if on else 0}")

    async def set_noise_reduction(self, on: bool) -> bool:
        return await self.set(f"NR0{1 if on else 0}")

    async def set_auto_notch(self, on: bool) -> bool:
        return await self.set(f"BC0{1 if on else 0}")

    async def set_compressor(self, on: bool) -> bool:
        return await self.set(f"PR0{1 if on else 0}")

    async def set_tuner(self, value: int) -> bool:
        return await self.set(f"AC{value:03d}")

    async def set_vfo(self, vfo: str) -> bool:
        cmd = "VS0" if vfo.upper() == "A" else "VS1"
        return await self.set(cmd)

    async def set_split(self, on: bool) -> bool:
        return await self.set(f"ST{1 if on else 0}")

    async def set_power(self, on: bool) -> bool:
        return await self.set(f"PS{1 if on else 0}")

    async def set_squelch(self, value: int) -> bool:
        return await self.set(f"SQ0{value:03d}")

    async def set_mic_gain(self, value: int) -> bool:
        return await self.set(f"MG{value:03d}")

    async def set_band_stack(self, bsr: int) -> bool:
        return await self.set(f"BS{bsr:02d}")

    # ── Scope/Spectrum Commands ────────────────────────────────────

    async def set_scope_span(self, span: int) -> bool:
        """Set scope span (0-9, see SCOPE_SPANS)."""
        return await self.set(f"SS05{span:02d}")

    async def set_scope_speed(self, speed: int) -> bool:
        """Set scope sweep speed (0-5)."""
        return await self.set(f"SS00{speed:02d}")

    async def set_scope_mode(self, mode: int) -> bool:
        """Set scope display mode (0-9)."""
        return await self.set(f"SS06{mode:02d}")

    async def set_nb_level(self, level: int) -> bool:
        """Set noise blanker level (0-10)."""
        return await self.set(f"NL0{level:02d}")

    async def set_nr_level(self, level: int) -> bool:
        """Set noise reduction level (1-15)."""
        return await self.set(f"RL{level:02d}")

    async def set_compressor_level(self, level: int) -> bool:
        """Set compressor level (1-100)."""
        return await self.set(f"PL{level:03d}")

    async def set_monitor(self, on: bool) -> bool:
        """Set monitor on/off."""
        return await self.set(f"ML0{1 if on else 0}")

    async def set_monitor_gain(self, value: int) -> bool:
        """Set monitor gain (0-100)."""
        return await self.set(f"ML1{value:03d}")

    async def set_vox(self, on: bool) -> bool:
        """Set VOX on/off."""
        return await self.set(f"VX{1 if on else 0}")

    async def set_break_in(self, on: bool) -> bool:
        """Set break-in on/off."""
        return await self.set(f"BI{1 if on else 0}")

    async def set_key_speed(self, speed: int) -> bool:
        """Set CW key speed (0-60)."""
        return await self.set(f"KS{speed:03d}")

    async def set_cw_pitch(self, pitch: int) -> bool:
        """Set CW pitch (0-75)."""
        return await self.set(f"KP{pitch:02d}")

    async def set_rit(self, on: bool) -> bool:
        """Set RIT on/off."""
        return await self.set(f"CF000{1 if on else 0:01d}")

    async def set_rit_freq(self, freq: int) -> bool:
        """Set RIT offset (-9999 to 9999 Hz)."""
        sign = '+' if freq >= 0 else '-'
        return await self.set(f"CF001{sign}{abs(freq):04d}")

    async def set_xit(self, on: bool) -> bool:
        """Set XIT on/off."""
        return await self.set(f"XT{1 if on else 0}")

    # ── Bulk State Query ──────────────────────────────────────────

    async def initial_state_sync(self) -> dict:
        """Perform a full state read after connection."""
        state = {}
        queries = [
            ("vfo_a_freq", "FA"),
            ("vfo_b_freq", "FB"),
            ("mode", "MD0"),
            ("tx_status", "TX"),
            ("s_meter", "SM0"),
            ("filter_width", "SH0"),
            ("af_gain_raw", "AG"),
            ("rf_power", "PC"),
            ("preamp", "PA0"),
            ("attenuator", "RA0"),
            ("noise_blanker", "NB0"),
            ("noise_reduction", "NR0"),
            ("auto_notch", "BC"),
            ("tuner_status", "AC"),
            ("power_on", "PS"),
        ]
        for field, cmd in queries:
            resp = await self.query(cmd)
            if resp:
                state[field] = resp
            await asyncio.sleep(0.05)
        return state

    # ── Reconnect ──────────────────────────────────────────────────

    async def reconnect_loop(self) -> bool:
        """Attempt reconnection with exponential backoff."""
        delay = RECONNECT_BASE_DELAY
        while True:
            logger.info("Attempting reconnect to %s (delay=%.1fs)...", self.port, delay)
            if await self.connect():
                logger.info("Reconnected to %s", self.port)
                return True
            await asyncio.sleep(delay)
            delay = min(delay * 2, RECONNECT_MAX_DELAY)
