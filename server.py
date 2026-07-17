#!/usr/bin/env python3
"""
FT-710 Web Control Server
=========================
FastAPI-based web server that bridges a browser to a Yaesu FT-710
radio via serial CAT protocol.  Provides a WebSocket endpoint for
real-time control and state updates, plus REST APIs for memory
channels and authentication.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import json
import logging
import os
import secrets as _secrets
import struct
import subprocess as _subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    SERIAL_PORT, BAUD_RATE, WEB_PORT, WEB_HOST, WEB_PASSWORD,
    SSL_CERTFILE, SSL_KEYFILE,
    SCOPE_SERIAL_PORT, SCOPE_BAUD_RATE, SCOPE_SPANS,
    AUTH_COOKIE, AUTH_TOKEN_BYTES, MEM_CHANNEL_COUNT, PTT_SAFETY_TIMEOUT,
    MODE_NUM_TO_NAME, MODE_NAME_TO_NUM, BANDS, UI_MODES,
    get_band_for_frequency, get_filter_widths_for_mode, get_filter_hz,
)
from cat_controller import CatController
from radio_state import RadioState
from poll_scheduler import PollScheduler
from scope_handler import ScopeHandler  # synthetic scope fallback
from scope_frame import parse_pipe_payload, WF_SIZE
from audio_handler import AudioHandler
from opus_rx import (
    RxOpusEncoder, TxOpusDecoder,
    AUDIO_TAG_PCM, AUDIO_TAG_OPUS, DEFAULT_BITRATE,
)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import (
    HTMLResponse, JSONResponse, RedirectResponse, FileResponse, Response,
)
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ft710")

# ── Global State ────────────────────────────────────────────────────
radio = RadioState()
cat: CatController | None = None
scheduler: PollScheduler | None = None
scope: ScopeHandler | None = None
audio: AudioHandler | None = None

# Connected clients
ctrl_clients: set[WebSocket] = set()
spectrum_clients: set[WebSocket] = set()
audio_rx_clients: set[WebSocket] = set()
audio_tx_clients: set[WebSocket] = set()
_last_meter_broadcast_log = 0.0
# Single-owner guard for the TX uplink: only the first connected TX client's
# audio is fed to the radio. Prevents two open tabs from interleaving mic
# frames into the same playback queue (garbled TX). A later client takes over
# only after the current owner disconnects.
_tx_owner_ws: Optional[WebSocket] = None
_state_broadcast_task: asyncio.Task | None = None
_scope_read_task: asyncio.Task | None = None
_scope_broadcast_task: asyncio.Task | None = None
_scope_proc: asyncio.subprocess.Process | None = None
_scope_pipe_lock: asyncio.Lock | None = None
_audio_rx_task: asyncio.Task | None = None
_audio_tx_task: asyncio.Task | None = None

# TX Opus decoder (browser mic → server)
_opus_tx_decoder: TxOpusDecoder | None = None

# RX broadcast pacing/guard rails
AUDIO_RX_SEND_TIMEOUT = 0.012          # per-frame per-client timeout (seconds)
AUDIO_RX_MAX_FRAMES_PER_CYCLE = 2      # cap burst send when loop catches up
RX_SILENCE_ALERT_S = 20                # zero-audio watchdog: alert after this many seconds of bit-exact silence
METER_BROADCAST_LOG_INTERVAL_SECONDS = 0.5

# Auth: valid session tokens (server-side, cleared on restart)
_auth_tokens: set[str] = set()

# Memory channels file
SCRIPT_DIR = Path(__file__).parent


def _runtime_dir() -> Path:
    """Return the directory containing runtime files for source or frozen mode."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return SCRIPT_DIR


def _scope_pipe_command() -> list[str] | None:
    """Return the command used to start the FT4222 scope pipe."""
    if getattr(sys, "frozen", False):
        exe_name = "scope_pipe.exe" if sys.platform == "win32" else "scope_pipe"
        pipe_exe = _runtime_dir() / exe_name
        if pipe_exe.exists():
            return [str(pipe_exe)]

    scope_pipe_path = SCRIPT_DIR / "scope_pipe.py"
    if scope_pipe_path.exists():
        return [sys.executable, str(scope_pipe_path)]
    return None


STATIC_DIR = _runtime_dir() / "static"
MEM_FILE = Path(os.environ.get("FT710_MEM_FILE", str(_runtime_dir() / "mem_channels.json")))

# ── Auth Helpers ────────────────────────────────────────────────────

# Rate limiting for login attempts
_login_attempts: dict[str, list[float]] = {}
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 300  # 5 minutes

def _check_login_rate_limit(ip: str) -> bool:
    """Check if IP has exceeded login attempt rate limit."""
    import time
    now = time.time()
    
    if ip not in _login_attempts:
        _login_attempts[ip] = []
    
    # Clean old attempts outside the window
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < _LOGIN_WINDOW_SECONDS]
    
    if len(_login_attempts[ip]) >= _LOGIN_MAX_ATTEMPTS:
        return False  # Rate limited
    
    _login_attempts[ip].append(now)
    return True

def _make_auth_token() -> str:
    """Generate a new random session token."""
    return _secrets.token_hex(AUTH_TOKEN_BYTES)

def _verify_auth(request: Request) -> bool:
    """Check whether the request carries a valid auth cookie or query-param token."""
    token = request.cookies.get(AUTH_COOKIE)
    if token and token in _auth_tokens:
        return True
    token = request.query_params.get("token")
    return token is not None and token in _auth_tokens

# ── Memory Channel Helpers ──────────────────────────────────────────

def _load_mem_channels() -> list:
    """Load memory channels from disk."""
    if MEM_FILE.exists():
        try:
            data = json.loads(MEM_FILE.read_text(encoding="utf-8"))
            channels = data.get("channels", [])
            # Pad to exactly MEM_CHANNEL_COUNT slots
            while len(channels) < MEM_CHANNEL_COUNT:
                channels.append(None)
            return channels[:MEM_CHANNEL_COUNT]
        except Exception:
            pass
    return [None] * MEM_CHANNEL_COUNT

def _save_mem_channels(channels: list):
    """Save memory channels to disk."""
    MEM_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEM_FILE.write_text(json.dumps({"channels": channels[:MEM_CHANNEL_COUNT]}, indent=2))

# ── Broadcast ───────────────────────────────────────────────────────

async def _broadcast_state():
    """Send dirty state fields to all connected WebSocket clients."""
    global ctrl_clients, _last_meter_broadcast_log
    dirty = radio.get_and_clear_dirty()
    if not dirty:
        return
    fields = radio.to_dirty_dict(dirty)
    meter_dirty = {
        "s_meter", "power_meter", "alc_meter", "swr_meter", "id_meter", "vd_meter",
    } & dirty
    now = time.monotonic()
    if meter_dirty and now - _last_meter_broadcast_log >= METER_BROADCAST_LOG_INTERVAL_SECONDS:
        _last_meter_broadcast_log = now
        logger.debug(
            "Meter broadcast dirty=%s raw={S=%s PWR=%s ALC=%s SWR=%s ID=%s VD=%s} "
            "derived={dBm=%.1f unit=%s W=%.1f ALC%%=%.0f SWR=%.1f Id=%.1f Vd=%.1f}",
            sorted(meter_dirty),
            fields.get("s_meter"),
            fields.get("power_meter"),
            fields.get("alc_meter"),
            fields.get("swr_meter"),
            fields.get("id_meter"),
            fields.get("vd_meter"),
            fields.get("s_meter_dbm", radio.s_meter_dbm),
            fields.get("s_unit", radio.s_unit),
            fields.get("power_watts", radio.power_watts),
            fields.get("alc_pct", radio.alc_pct),
            fields.get("swr_ratio", radio.swr_ratio),
            fields.get("id_amps", radio.id_amps),
            fields.get("vd_volts", radio.vd_volts),
        )
    update = {
        "type": "stateUpdate",
        "fields": fields,
        "dirty": list(dirty),
    }
    data = json.dumps(update)
    dead: set[WebSocket] = set()
    for ws in ctrl_clients:
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    ctrl_clients -= dead

async def _broadcast_mem_channels():
    """Send memory channels to all connected clients."""
    global ctrl_clients
    channels = _load_mem_channels()
    msg = json.dumps({"type": "memChannels", "channels": channels})
    dead: set[WebSocket] = set()
    for ws in ctrl_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    ctrl_clients -= dead

# ── Spectrum/Scope ───────────────────────────────────────────────────

async def _on_scope_frame(_scope: ScopeHandler):
    """Called when a new scope frame is parsed.  Merges key metadata
    into the global radio state and marks dirty for broadcast.
    Also feeds radio state back into scope for S-meter fallback."""
    if _scope.last_update > 0:
        changes = {}
        # S-meter from scope is 30 fps (vs 10 fps CAT) — safe to merge
        # because CAT corrects it every 100 ms.
        if _scope.s_meter >= 0:
            changes["s_meter"] = _scope.s_meter
        # vfo_a_freq / mode / preamp / attenuator are deliberately NOT
        # taken from scope frames.  The CAT poll path is the single source
        # of truth for these fields — scope data can lag behind user
        # commands and would fight the poll for control, causing the
        # displayed frequency to drift or "adjust itself".
        if _scope.scope_span >= 0:
            changes["scope_span"] = _scope.scope_span
        if _scope.scope_mode >= 0:
            changes["scope_mode"] = _scope.scope_mode
        if _scope.scope_start_freq >= 0:
            changes["scope_start_freq"] = _scope.scope_start_freq
        if changes:
            radio.update(**changes)
            await _broadcast_state()

async def _broadcast_spectrum_loop():
    """Periodically send spectrum data to all spectrum WebSocket clients.

    Runs at ~30 fps (33ms interval), matching typical scope update rate.
    Sends binary frames: 1-byte version + 850 bytes wf1 + 850 bytes wf2.

    When scope_pipe is not connected (no FT4222 data), falls back to
    S-meter-based synthetic spectrum from the CAT polling data.

    Idle (0 clients): sleeps 500ms instead of 33ms, cutting ~93% of
    idle wakeups.  Synthetic Gaussian generation is also skipped.
    """
    global scope, spectrum_clients
    interval = 1.0 / 5.0      # ~200ms → 5 fps
    idle_interval = 0.500      # 500 ms deep-sleep when no listeners
    _first = True
    _idle_skipped = 0
    while True:
        try:
            if not spectrum_clients:
                _idle_skipped += 1
                await asyncio.sleep(idle_interval)
                continue

            if scope:
                if not scope.connected:
                    # No FT4222 data — use S-meter fallback
                    scope.update_from_radio_state(radio)
                binary = scope.get_spectrum_binary()
                if _first:
                    mode = "FT4222" if scope.connected else "S-meter fallback"
                    logger.info("Spectrum broadcast active: %s, %d bytes/frame, %d clients",
                                mode, len(binary), len(spectrum_clients))
                    _first = False
                dead: set[WebSocket] = set()
                for ws in spectrum_clients:
                    try:
                        await ws.send_bytes(binary)
                    except Exception:
                        dead.add(ws)
                spectrum_clients -= dead
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning("Spectrum broadcast error: %s", e)
        await asyncio.sleep(interval)


async def _read_scope_pipe(proc):
    """Read binary spectrum frames from scope_pipe subprocess stdout.

    Frame format: 4-byte BE uint32 length + payload bytes.
    Heartbeat (len=0) means pipe is alive but idle.

    Updates global scope handler's spectrum data in-place.
    Stderr lines starting with "STATUS:" are machine-parseable status
    messages from the pipe process.
    """
    global scope, _scope_proc, _scope_read_task
    logger.info("Reading from scope_pipe (pid=%d)...", proc.pid)
    _first_frame = True
    _stderr_task = None

    async def _drain_stderr():
        """Continuously read stderr and log STATUS lines at INFO level."""
        try:
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if text.startswith("STATUS:"):
                    payload = text[7:]
                    # Log important status messages at INFO level
                    if any(kw in payload for kw in (
                        "fatal:", "pipe_error:", "spi_init_failed",
                        "too_many_errors", "reinitializing_device",
                        "sync_lost", "sync_recovered",
                    )):
                        logger.warning("scope_pipe: %s", payload)
                    elif "heartbeat:" in payload or "diag:" in payload:
                        logger.debug("scope_pipe: %s", payload)
                    else:
                        logger.info("scope_pipe: %s", payload)
                else:
                    logger.debug("scope_pipe(stderr): %s", text)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("scope_pipe stderr drain: %s", e)

    # Start stderr reader in background
    _stderr_task = asyncio.create_task(_drain_stderr(), name="scope_stderr")

    try:
        while True:
            # Read 4-byte length header
            header = await proc.stdout.read(4)
            if not header or len(header) < 4:
                break

            frame_len = struct.unpack('>I', header)[0]

            # Heartbeat frame (len=0): pipe is alive but no data
            if frame_len == 0:
                continue

            if frame_len < 1 or frame_len > 8192:
                logger.warning("scope_pipe: bad frame length %d", frame_len)
                continue

            # Read payload
            payload = await proc.stdout.read(frame_len)
            if len(payload) < frame_len:
                break

            # Parse pipe payload
            if scope and len(payload) >= 1 + WF_SIZE:
                try:
                    parsed = parse_pipe_payload(payload)
                except ValueError as e:
                    logger.warning("scope_pipe: bad payload: %s", e)
                    continue

                scope.spectrum_rx1 = parsed.wf1
                scope.spectrum_rx2 = parsed.wf2
                scope.scope_mode = parsed.scope_mode
                scope.scope_span = parsed.scope_span
                scope.preamp = parsed.preamp
                scope.attenuator = parsed.attenuator
                scope.mode = parsed.mode
                scope.s_meter = parsed.s_meter
                scope.vfoa_freq = parsed.vfoa_freq
                scope.scope_start_freq = parsed.scope_start_freq
                scope._frame_count += 1
                scope.last_update = time.time()

                # Mark scope as connected on first successful frame
                if _first_frame:
                    _first_frame = False
                    scope._connected = True
                    logger.info("scope_pipe: first frame received — spectrum active "
                                "(span=%d, s_meter=%d, wf1_max=%d)",
                                parsed.scope_span, parsed.s_meter, max(parsed.wf1))

                await _on_scope_frame(scope)

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning("scope_pipe read error: %s", e)
    finally:
        # Clean up stderr reader
        if _stderr_task:
            _stderr_task.cancel()
            try:
                await _stderr_task
            except asyncio.CancelledError:
                pass

        logger.warning("scope_pipe exited (frames=%d, connected=%s)",
                       scope._frame_count if scope else 0,
                       scope._connected if scope else False)
        if scope:
            scope._connected = False
        if proc.returncode is None:
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                try:
                    await proc.wait()
                except Exception:
                    pass
        if _scope_proc is proc:
            _scope_proc = None
        if _scope_read_task is asyncio.current_task():
            _scope_read_task = None

        # ── Auto-restart ──────────────────────────────────────────
        # If spectrum clients are still connected when the pipe exits,
        # restart it after a short delay (1s) so transient USB glitches
        # don't require a manual client reconnect.
        if spectrum_clients and _scope_pipe_command():
            logger.info("scope_pipe exited with %d spectrum client(s) — "
                        "will restart in 1s", len(spectrum_clients))
            await asyncio.sleep(1.0)
            # Only restart if no other pipe has been started in the meantime
            if _scope_proc is None:
                await _ensure_scope_pipe_running()


async def _ensure_scope_pipe_running():
    """Start the FT4222 scope subprocess only while spectrum clients exist."""
    global _scope_read_task, _scope_proc, _scope_pipe_lock
    if _scope_read_task and not _scope_read_task.done():
        return
    if _scope_pipe_lock is None:
        _scope_pipe_lock = asyncio.Lock()
    async with _scope_pipe_lock:
        if _scope_read_task and not _scope_read_task.done():
            return
        scope_pipe_cmd = _scope_pipe_command()
        if not scope_pipe_cmd:
            logger.warning("scope_pipe worker not found — spectrum will use S-meter fallback only")
            return
        logger.info("Starting scope_pipe subprocess for spectrum client...")
        try:
            _scope_proc = await asyncio.create_subprocess_exec(
                *scope_pipe_cmd,
                stdout=_subprocess.PIPE, stderr=_subprocess.PIPE,
            )
            _scope_read_task = asyncio.create_task(
                _read_scope_pipe(_scope_proc), name="scope_pipe_read"
            )
            logger.info("scope_pipe subprocess started (pid=%d)", _scope_proc.pid)
        except Exception as e:
            _scope_proc = None
            _scope_read_task = None
            logger.warning("Failed to start scope_pipe: %s", e)
            logger.warning("Spectrum will use S-meter fallback only")


async def _stop_scope_pipe():
    """Stop the FT4222 scope subprocess when no spectrum clients remain."""
    global _scope_read_task, _scope_proc, scope
    task = _scope_read_task
    _scope_read_task = None
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
    proc = _scope_proc
    _scope_proc = None
    if proc and proc.returncode is None:
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                await proc.wait()
            except Exception:
                pass
        except Exception:
            pass
    if scope:
        scope._connected = False

# ── Audio Broadcast ────────────────────────────────────────────────────

async def _send_audio_frames_to_clients(
    frames: list[bytes],
    clients: set[WebSocket],
    per_frame_timeout: float = AUDIO_RX_SEND_TIMEOUT,
) -> set[WebSocket]:
    """Send encoded RX audio frames to clients with timeout isolation.

    A single slow/backpressured client must not block the whole audio loop.
    Returns the subset of clients that errored/timed out and should be removed.
    """
    if not frames or not clients:
        return set()

    # Snapshot to keep gather/zip pairing stable even if caller mutates set later.
    clients_snapshot = list(clients)

    async def _send_one(ws: WebSocket):
        for frame in frames:
            await asyncio.wait_for(ws.send_bytes(frame), timeout=per_frame_timeout)

    results = await asyncio.gather(
        *[_send_one(ws) for ws in clients_snapshot],
        return_exceptions=True,
    )
    dead: set[WebSocket] = set()
    for ws, res in zip(clients_snapshot, results):
        if isinstance(res, Exception):
            dead.add(ws)
    return dead

async def _audio_rx_loop():
    """Capture RX audio from the sound card and broadcast to clients.

    Reads int16 PCM chunks from the audio handler, encodes via Opus (or
    sends raw PCM), and broadcasts to all connected audio_rx_clients.

    Idle (0 clients): skips PCM reads entirely and sleeps 500ms instead
    of 20ms, cutting ~96% of wakeups.  On client arrival the next 20ms
    tick catches the small accumulated buffer with no perceptible delay.
    """
    global audio, audio_rx_clients
    interval = 0.020       # 20 ms chunk interval (active)
    idle_interval = 0.500  # 500 ms deep-sleep when no listeners
    _first = True
    _loop_count = 0
    _pcm_count = 0
    _send_count = 0
    _trimmed_bursts = 0
    _idle_skipped = 0
    while True:
        try:
            _loop_count += 1
            if audio and audio._rx_running:
                # ── Idle: no clients → skip PCM read entirely ──────
                # PCM read + resample + Opus encode is the #1 CPU
                # consumer when idle.  Skip everything, sleep deep.
                if not audio_rx_clients:
                    _idle_skipped += 1
                    if _loop_count % 500 == 0 and _idle_skipped > 50:
                        logger.info(
                            "Audio loop idle: %d skips so far, entering deep-sleep",
                            _idle_skipped,
                        )
                    await asyncio.sleep(idle_interval)
                    continue

                pcm = audio.read_rx_chunk()
                audio.note_rx_chunk(pcm)
                if pcm:
                    _idle_skipped = 0
                    _pcm_count += 1
                    frames = audio.encode_rx_audio(pcm)

                    if frames:
                        # If the loop fell behind and produced multiple Opus
                        # packets at once, prioritize freshest audio to keep
                        # end-to-end latency bounded.
                        if len(frames) > AUDIO_RX_MAX_FRAMES_PER_CYCLE:
                            _trimmed_bursts += 1
                            frames = frames[-AUDIO_RX_MAX_FRAMES_PER_CYCLE:]
                        _send_count += 1
                        if _first:
                            tag_name = "Opus" if audio.opus_enabled else "Int16 PCM"
                            # Check audio level (safely)
                            _slice = pcm[:200]
                            _sample_count = len(_slice) // 2
                            if _sample_count > 0:
                                import struct as _struct
                                _samples = _struct.unpack(f"<{_sample_count}h", _slice[:_sample_count*2])
                                _peak = max(abs(s) for s in _samples) / 32767 * 100
                                logger.info("RX audio broadcast active: %s, %d clients, peak=%.1f%%",
                                           tag_name, len(audio_rx_clients), _peak)
                                if _peak < 0.5:
                                    logger.warning("RX audio is near-silent (peak=%.1f%%) — "
                                                 "check radio AF gain / USB audio connection", _peak)
                            _first = False
                        dead = await _send_audio_frames_to_clients(frames, audio_rx_clients)
                        if dead:
                            logger.warning("Removed %d dead/slow audio clients", len(dead))
                            audio_rx_clients -= dead
            # Periodic health log
            if _loop_count % 250 == 0 and _idle_skipped == 0:  # Every ~5s when active
                logger.debug("Audio loop: loops=%d pcm_chunks=%d sends=%d trimmed=%d clients=%d running=%s peak=%d",
                           _loop_count, _pcm_count, _send_count,
                           _trimmed_bursts,
                           len(audio_rx_clients), audio._rx_running if audio else False,
                           audio._rx_last_peak if audio else 0)
                # RX silence watchdog: bit-exact zeros while the squelch is
                # open mean the FT-710 USB audio is muted/wedged (a quiet band
                # is never bit-exact silent). Flag it so the UI can warn.
                if audio and radio and cat and cat.connected:
                    _silent_s = audio.rx_silent_seconds()
                    if (_silent_s >= RX_SILENCE_ALERT_S and radio.squelch_open
                            and not radio.rx_audio_silent):
                        radio.update(rx_audio_silent=True)
                        logger.warning(
                            "RX audio bit-exact silent for %.0fs with squelch open — "
                            "FT-710 USB audio may be wedged; power-cycle the radio "
                            "or re-plug its USB cable", _silent_s)
                        await _broadcast_state()
                    elif _silent_s < 1.0 and radio.rx_audio_silent:
                        radio.update(rx_audio_silent=False)
                        logger.info("RX audio recovered (non-zero samples)")
                        await _broadcast_state()
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.warning("Audio RX broadcast error: %s", e)
            import traceback; traceback.print_exc()
        await asyncio.sleep(interval)


async def _audio_tx_drain_loop():
    """Periodically drain queued TX audio to the sound card output.

    Offloads the synchronous PyAudio write to a thread so it never
    blocks the asyncio event loop.  Without this, a slow audio write
    can stall all other async work — including CAT commands and state
    broadcasts — causing UI stutter on both audio and CAT.

    Idle (no pending TX): sleeps 200ms instead of 50ms, cutting
    ~75% of idle wakeups.
    """
    global audio
    active_interval = 0.010  # 10 ms drain interval during TX playback
    idle_interval = 0.200    # 200 ms deep-idle when no TX audio pending
    while True:
        try:
            if audio and audio.has_pending_tx_audio():
                await asyncio.to_thread(audio.write_tx_chunk)
        except asyncio.CancelledError:
            return
        except Exception:
            pass
        await asyncio.sleep(
            active_interval if audio and audio.has_pending_tx_audio() else idle_interval
        )


# ── Command Handler ─────────────────────────────────────────────────

async def _handle_ws_message(ws: WebSocket, msg_str: str):
    """Process incoming WebSocket control messages.

    Message format: JSON with 'type' and 'field'/'value'.
    """
    try:
        msg = json.loads(msg_str)
    except json.JSONDecodeError:
        # Fall back to legacy text format: "field:value"
        if ":" in msg_str:
            field, _, val = msg_str.partition(":")
            msg = {"type": "set", "field": field, "value": val}
        else:
            logger.debug("Invalid message: %s", msg_str[:80])
            return

    msg_type = msg.get("type", "")
    field = msg.get("field", "")
    value = msg.get("value")

    if msg_type == "ping":
        await ws.send_text(json.dumps({"type": "pong"}))

    elif msg_type == "get":
        if field == "fullState":
            await ws.send_text(json.dumps({
                "type": "fullState",
                "data": radio.to_dict(),
            }))
        else:
            full = radio.to_dict()
            if field in full:
                await ws.send_text(json.dumps({
                    "type": "value", "field": field, "value": full[field],
                }))

    elif msg_type == "memRecall":
        # Atomic memory channel recall: send frequency + mode in a single
        # message so the poll cycle cannot capture the intermediate state
        # between two separate CAT commands.  Order matters — see below.
        if cat is None or not cat.connected:
            await ws.send_text(json.dumps({
                "type": "error", "message": "Radio not connected",
            }))
            return

        freq = msg.get("freq")
        mode_name = msg.get("mode")
        vfo = str(msg.get("vfo") or radio.active_vfo or "A").upper()
        if vfo not in ("A", "B"):
            await ws.send_text(json.dumps({
                "type": "error", "message": f"Unknown VFO: {vfo}",
            }))
            return
        logger.info(
            "Memory recall: freq=%s mode=%s vfo=%s", freq, mode_name, vfo,
        )
        if freq is not None:
            scheduler and scheduler.note_user_command()
            # Skip polls for 2 s so they don't capture stale intermediate
            # state while the two CAT commands are in flight.
            scheduler and scheduler.skip_next_poll("if", 2.0)
            scheduler and scheduler.skip_next_poll("vfo", 2.0)
            # CRITICAL ORDER: frequency FIRST, then mode.
            # The FT-710 band stacking register auto-recalls the last-used
            # mode whenever the frequency changes bands.  If we sent mode
            # first, the subsequent frequency change could revert it.
            # Setting mode AFTER frequency overrides band-stack auto-recall.
            await cat.set_frequency(int(freq), vfo)
            if vfo.upper() == "B":
                radio.update(vfo_b_freq=int(freq))
            else:
                radio.update(vfo_a_freq=int(freq), active_vfo="A")
        if mode_name is not None:
            mode_num = MODE_NAME_TO_NUM.get(str(mode_name).upper())
            if mode_num is not None:
                await cat.set_mode(mode_num)
                radio.update(mode=mode_num)
                scheduler and scheduler.skip_next_poll("if", 2.0)
                if freq is not None:
                    # SSB mode changes can shift the carrier/displayed
                    # frequency by the sideband offset (observed ±1400 Hz
                    # on FT-710).  Set the stored frequency again after MD0
                    # so the final polled frequency matches the memory slot.
                    await cat.set_frequency(int(freq), vfo)
                    if vfo == "B":
                        radio.update(vfo_b_freq=int(freq))
                    else:
                        radio.update(vfo_a_freq=int(freq))
                    scheduler and scheduler.skip_next_poll("if", 2.0)
                    scheduler and scheduler.skip_next_poll("vfo", 2.0)
            else:
                logger.warning("Memory recall: unknown mode %r", mode_name)

    elif msg_type == "set":
        await _execute_set_command(field, value, ws)

    elif msg_type == "memLoadAll":
        await _broadcast_mem_channels()

    elif msg_type == "memSave":
        channels = msg.get("channels", [])
        _save_mem_channels(channels)
        await _broadcast_mem_channels()

    elif msg_type == "memDelete":
        index = msg.get("index", -1)
        if 0 <= index < MEM_CHANNEL_COUNT:
            channels = _load_mem_channels()
            channels[index] = None
            _save_mem_channels(channels)
            await _broadcast_mem_channels()


async def _execute_set_command(field: str, value, ws: WebSocket):
    """Execute a set command against the radio."""
    global cat, radio, scheduler

    if cat is None or not cat.connected:
        await ws.send_text(json.dumps({
            "type": "error", "message": "Radio not connected",
        }))
        return

    # Brief pause of background polling so the user's next command
    # doesn't queue behind a poll cycle on the serial lock.
    scheduler and scheduler.note_user_command()

    try:
        if field == "freq":
            # "freq" targets whichever VFO is currently active on the radio,
            # so web tuning actually affects the receiving VFO.  (Explicit
            # vfo_a_freq / vfo_b_freq below force a specific VFO.)
            freq = int(value)
            vfo = radio.active_vfo or "A"
            # Skip poll BEFORE sending CAT command so in-flight poll
            # results don't overwrite our new setting (same race as band).
            scheduler and scheduler.skip_next_poll("if", 1.0)
            await cat.set_frequency(freq, vfo)
            if vfo == "B":
                radio.update(vfo_b_freq=freq)
            else:
                radio.update(vfo_a_freq=freq)

        elif field == "vfo_a_freq":
            freq = int(value)
            scheduler and scheduler.skip_next_poll("if", 1.0)
            await cat.set_frequency(freq, "A")
            radio.update(vfo_a_freq=freq)

        elif field == "vfo_b_freq":
            freq = int(value)
            scheduler and scheduler.skip_next_poll("vfo", 1.0)
            await cat.set_frequency(freq, "B")
            radio.update(vfo_b_freq=freq)

        elif field == "mode":
            mode_name = str(value).upper()
            mode_num = MODE_NAME_TO_NUM.get(mode_name)
            if mode_num is not None:
                await cat.set_mode(mode_num)
                radio.update(mode=mode_num)
                scheduler and scheduler.skip_next_poll("if", 1.0)
            else:
                await ws.send_text(json.dumps({
                    "type": "error", "message": f"Unknown mode: {value}",
                }))

        elif field == "ptt":
            tx = value is True or str(value).lower() == "true"
            if tx:
                # Key radio first so the TX light comes on immediately,
                # THEN open the audio output stream synchronously —
                # awaiting start_tx here avoids a race where the drain
                # loop queues mic frames before the PortAudio stream is
                # open and start_tx's queue-clearing discards them.
                # start_tx() is idempotent — if a stream is already active
                # it returns immediately without clearing the queue.
                await cat.set_ptt(True)
                radio.update(tx_status=1)
                if audio:
                    ok = await asyncio.to_thread(audio.start_tx)
                    if not ok:
                        # Audio path failed to open — the radio is keyed but
                        # has no modulation.  Drop PTT immediately so the
                        # user sees the failure and can try again, rather
                        # than silently transmitting a dead carrier.
                        logger.error("PTT: TX audio stream failed — unkeying radio")
                        await cat.set_ptt(False)
                        radio.update(tx_status=0, power_meter=0, alc_meter=0,
                                     swr_meter=0, comp_meter=0, id_meter=0)
                        await ws.send_text(json.dumps({
                            "type": "error",
                            "message": "TX audio device unavailable — PTT released. Try again.",
                        }))
                        scheduler and scheduler.skip_next_poll("tx_status", 1.0)
                        return
            else:
                # Graceful TX stop: drain queued audio to the DAC and block
                # until it has played (Pa_StopStream semantics), so word-
                # endings go out over RF before we drop PTT. Must run off the
                # event loop — the blocking drain can take up to TX_DRAIN_MS.
                if audio:
                    await asyncio.to_thread(audio.stop_tx, True)
                # Drop PTT immediately after the drain.  No verify loop:
                # the radio obeys TX0 on the first write, and the TX-status
                # poll (plus the client PTT watchdog) catches a stuck keyup.
                # The previous 3×200 ms verify loop added ~600 ms to release.
                await cat.set_ptt(False)
                radio.update(tx_status=0, power_meter=0, alc_meter=0,
                             swr_meter=0, comp_meter=0, id_meter=0)
            scheduler and scheduler.skip_next_poll("tx_status", 1.0)

        elif field == "tune":
            on = value is True or str(value).lower() == "true"
            if on:
                # Start low-power carrier for tuning (TX2)
                await cat.set_tune(True)
                radio.update(tx_status=2)
                # After carrier stabilises, trigger the antenna tuner.
                # AC003 = P1=0,P2=0,P3=3 → Tuning Start (standard tuner).
                await asyncio.sleep(0.3)
                await cat.send_priority_set_command("AC003")
                radio.update(tuner_status=2)
            else:
                # Drop carrier — stop tuner if still running, then end TX.
                await cat.send_priority_set_command("AC000")
                await cat.set_tune(False)
                radio.update(tx_status=0, tuner_status=0)
            scheduler and scheduler.skip_next_poll("tx_status", 1.0)

        elif field == "filter" or field == "filter_width":
            idx = int(value)
            logger.info("Filter set command: index=%d", idx)
            scheduler and scheduler.skip_next_poll("filter_width", 3.0)
            ok = await cat.set_filter_width(idx)
            logger.info("Filter set result: ok=%s index=%d", ok, idx)
            if ok:
                # Read back the radio's actual width instead of trusting
                # the write: the FT-710 silently ignores a width index
                # that is invalid for the current mode, and an optimistic
                # update would then linger ~4s before the post-skip poll
                # corrects it.  Skip window (3s) covers this query.
                await asyncio.sleep(0.15)
                actual = await cat.get_filter_width()
                logger.info("Filter read-back: index=%s (requested %d)", actual, idx)
                radio.update(filter_width=actual if actual is not None else idx)
            else:
                await ws.send_text(json.dumps({
                    "type": "error",
                    "message": f"Filter width command failed: {idx}",
                }))

        elif field == "af_gain":
            v = max(0, min(255, int(value)))
            await cat.set_af_gain(v)
            radio.update(af_gain=v)
            scheduler and scheduler.skip_next_poll("af_gain", 3.0)

        elif field == "rf_power":
            v = max(5, min(100, int(value)))
            await cat.set_rf_power(v)
            radio.update(rf_power=v)
            scheduler and scheduler.skip_next_poll("rf_power", 3.0)

        elif field == "preamp":
            v = int(value)
            if v in (0, 1, 2):
                await cat.set_preamp(v)
                radio.update(preamp=v)
                scheduler and scheduler.skip_next_poll("preamp", 3.0)

        elif field == "att" or field == "attenuator":
            v = int(value)
            if v in (0, 1, 2, 3):
                await cat.set_attenuator(v)
                radio.update(attenuator=v)
                scheduler and scheduler.skip_next_poll("attenuator", 3.0)

        elif field == "nb" or field == "noise_blanker":
            on = value is True or str(value).lower() in ("true", "1")
            await cat.set_noise_blanker(on)
            radio.update(noise_blanker=on)
            scheduler and scheduler.skip_next_poll("noise_blanker", 3.0)

        elif field == "nr" or field == "noise_reduction":
            on = value is True or str(value).lower() in ("true", "1")
            await cat.set_noise_reduction(on)
            radio.update(noise_reduction=on)
            scheduler and scheduler.skip_next_poll("noise_reduction", 3.0)

        elif field == "an" or field == "auto_notch":
            on = value is True or str(value).lower() in ("true", "1")
            await cat.set_auto_notch(on)
            radio.update(auto_notch=on)
            scheduler and scheduler.skip_next_poll("auto_notch", 3.0)

        elif field == "comp" or field == "compressor":
            on = value is True or str(value).lower() in ("true", "1")
            await cat.set_compressor(on)
            radio.update(compressor=on)
            scheduler and scheduler.skip_next_poll("compressor", 5.0)

        elif field == "tuner":
            v = int(value)
            if v in (0, 1, 2):
                await cat.set_tuner(v)
                radio.update(tuner_status=v)
                scheduler and scheduler.skip_next_poll("tuner_status", 3.0)

        elif field == "vfo":
            vfo = str(value).upper()
            if vfo in ("A", "B"):
                await cat.set_vfo(vfo)
                radio.update(active_vfo=vfo)

        elif field == "split":
            on = value is True or str(value).lower() in ("true", "1")
            await cat.set_split(on)
            radio.update(split=on)

        elif field == "power":
            on = value is True or str(value).lower() in ("true", "1")
            await cat.set_power(on)
            radio.update(power_on=on)

        elif field == "squelch":
            v = max(0, min(100, int(value)))
            await cat.set_squelch(v)
            radio.update(squelch=v)

        elif field == "mic_gain":
            v = max(0, min(100, int(value)))
            await cat.set_mic_gain(v)
            radio.update(mic_gain=v)

        elif field == "scope_span":
            v = int(value)
            if 0 <= v <= 9:
                await cat.set_scope_span(v)
                radio.update(scope_span=v)
                scheduler and scheduler.skip_next_poll("scope_span", 3.0)

        elif field == "scope_speed":
            v = int(value)
            if 0 <= v <= 5:
                await cat.set_scope_speed(v)
                radio.update(scope_speed=v)

        elif field == "scope_mode":
            v = int(value)
            if 0 <= v <= 9:
                await cat.set_scope_mode(v)
                radio.update(scope_mode=v)

        elif field == "nb_level":
            v = max(0, min(10, int(value)))
            await cat.set_nb_level(v)
            radio.update(nb_level=v)

        elif field == "nr_level":
            v = max(1, min(15, int(value)))
            await cat.set_nr_level(v)
            radio.update(nr_level=v)

        elif field == "comp_level" or field == "compressor_level":
            v = max(1, min(100, int(value)))
            await cat.set_compressor_level(v)
            radio.update(compressor_level=v)

        elif field == "monitor":
            on = value is True or str(value).lower() in ("true", "1")
            await cat.set_monitor(on)

        elif field == "vox":
            on = value is True or str(value).lower() in ("true", "1")
            await cat.set_vox(on)
            radio.update(vox=on)

        elif field == "break_in":
            on = value is True or str(value).lower() in ("true", "1")
            await cat.set_break_in(on)
            radio.update(break_in=on)

        elif field == "key_speed":
            v = max(0, min(60, int(value)))
            await cat.set_key_speed(v)

        elif field == "cw_pitch":
            v = max(0, min(75, int(value)))
            await cat.set_cw_pitch(v)

        elif field == "rit":
            on = value is True or str(value).lower() in ("true", "1")
            await cat.set_rit(on)

        elif field == "rit_freq":
            v = max(-9999, min(9999, int(value)))
            await cat.set_rit_freq(v)

        elif field == "xit":
            on = value is True or str(value).lower() in ("true", "1")
            await cat.set_xit(on)

        elif field == "meter_display":
            v = int(value)
            if 0 <= v <= 5:
                await cat.set_meter_display(v)
                radio.update(meter_display=v)
                scheduler and scheduler.skip_next_poll("meter_display", 3.0)

        elif field == "amc_level":
            v = max(1, min(100, int(value)))
            await cat.set_amc_level(v)
            radio.update(amc_level=v)
            scheduler and scheduler.skip_next_poll("amc_level", 5.0)

        elif field == "rf_gain":
            v = max(0, min(255, int(value)))
            await cat.set_rf_gain(v)
            radio.update(rf_gain=v)
            scheduler and scheduler.skip_next_poll("rf_gain", 3.0)

        elif field == "scope_on":
            on = value is True or str(value).lower() in ("true", "1")
            await cat.set_scope_on(on)
            radio.update(scope_on=on)
            scheduler and scheduler.skip_next_poll("scope_on", 3.0)

        elif field == "antenna":
            v = int(value)
            if 1 <= v <= 3:
                await cat.set_antenna(v)
                radio.update(antenna=v)
                scheduler and scheduler.skip_next_poll("antenna", 3.0)

        elif field == "agc":
            v = int(value)
            if 0 <= v <= 3:
                await cat.set_agc(v)
                radio.update(agc=v)
                scheduler and scheduler.skip_next_poll("agc", 3.0)

        elif field == "dnr" or field == "dnr_level":
            v = max(0, min(15, int(value)))
            await cat.set_dnr(v)
            radio.update(dnr_level=v)
            scheduler and scheduler.skip_next_poll("dnr_level", 3.0)

        elif field == "contour" or field == "contour_level":
            v = max(0, min(255, int(value)))
            await cat.set_contour(v)
            radio.update(contour_level=v)
            scheduler and scheduler.skip_next_poll("contour_level", 5.0)

        elif field == "drive":
            # Drive maps to RF Power (PC) on FT-710 Yaesu
            v = max(5, min(100, int(value)))
            await cat.set_drive(v)
            radio.update(rf_power=v)
            scheduler and scheduler.skip_next_poll("rf_power", 3.0)

        elif field == "band":
            # Set band by name
            band_name = str(value)
            band = next((b for b in BANDS if b["name"] == band_name), None)
            if band:
                logger.info(
                    "Band change request: name=%s bsr=%02d default_freq=%d active_vfo=%s",
                    band["name"], band["bsr"], band["default_freq"], radio.active_vfo,
                )
                # Skip the next IF poll BEFORE sending CAT commands so that
                # any in-flight poll result (which may have already read the
                # old frequency) is discarded rather than overwriting our new
                # setting.  See poll_scheduler._poll_if for the counterpart.
                scheduler and scheduler.skip_next_poll("if", 1.0)
                scheduler and scheduler.skip_next_poll("vfo", 1.0)
                bs_ok = await cat.set_band_stack(band["bsr"])
                fa_ok = await cat.set_frequency(band["default_freq"], "A")
                # FT-710 band stacking auto-recalls the last-used mode for
                # the new band.  Explicitly set a sensible default so the
                # web UI and saved memory channels see a predictable mode.
                default_mode = 0x01 if band["default_freq"] < 10_000_000 \
                    else 0x02  # LSB below 10 MHz, USB above
                md_ok = await cat.set_mode(default_mode)
                if bs_ok and fa_ok:
                    radio.update(
                        vfo_a_freq=band["default_freq"],
                        active_vfo="A",
                        mode=default_mode,
                    )
                    logger.info(
                        "Band change applied: name=%s BS%02d OK FA%09d OK "
                        "MD0%X OK local_band=%s mode=%s",
                        band["name"], band["bsr"], band["default_freq"],
                        default_mode, radio.band_name, radio.mode_name,
                    )
                else:
                    # CAT command(s) failed — don't update server state,
                    # let the next poll cycle correct things.  Tell the
                    # client so it can revert its optimistic update.
                    failed = []
                    if not bs_ok:
                        failed.append(f"band stack BS{band['bsr']:02d}")
                    if not fa_ok:
                        failed.append(f"frequency FA{band['default_freq']:09d}")
                    if not md_ok:
                        failed.append(f"mode MD0{default_mode:X}")
                    logger.error(
                        "Band change FAILED: name=%s failed_commands=%s",
                        band["name"], failed,
                    )
                    await ws.send_text(json.dumps({
                        "type": "error",
                        "message": f"Band change to {band['name']} failed: {', '.join(failed)}",
                    }))
                    # Skip the broadcast at the end — poll will correct state
                    return
            else:
                logger.warning("Band change rejected: unknown band=%r", band_name)
                await ws.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown band: {band_name}",
                }))

        elif field == "vfo_equal":
            # A = B: copy VFO-B to VFO-A
            scheduler and scheduler.skip_next_poll("if", 1.0)
            await cat.set_frequency(radio.vfo_b_freq, "A")
            radio.update(vfo_a_freq=radio.vfo_b_freq)

        elif field == "vfo_swap":
            # Swap VFO-A and VFO-B
            fa = radio.vfo_a_freq
            fb = radio.vfo_b_freq
            scheduler and scheduler.skip_next_poll("if", 1.0)
            scheduler and scheduler.skip_next_poll("vfo", 1.0)
            await cat.set_frequency(fb, "A")
            await cat.set_frequency(fa, "B")
            radio.update(vfo_a_freq=fb, vfo_b_freq=fa)

        # After executing, broadcast immediately
        await _broadcast_state()

    except Exception as e:
        logger.error("Command error (%s=%s): %s", field, value, e)
        await ws.send_text(json.dumps({
            "type": "error", "message": str(e),
        }))


# ── Initial State Sync ──────────────────────────────────────────────

async def _init_scope_cat():
    """Send scope-initialization CAT commands via the CAT serial port.

    These extended commands configure the FT-710's scope display engine.
    Adapted from wfview's yaesuUdpControl scope init sequence.

    Commands are sent as extended CAT register writes. The FT-710 needs
    these to enable scope data output on the FT4222 SPI bus.

    Attempts scope init even when CAT reports as not-connected — the
    serial port may be open but the radio didn't respond to ID;.
    """
    global cat
    if cat is None:
        logger.warning("No CAT controller — skipping scope-init commands")
        return

    # Try to connect if not already connected (scope may work even
    # without full radio response to ID;)
    if not cat.connected:
        logger.info("CAT not connected — attempting scope-init anyway")
        try:
            await cat.connect()
        except Exception as e:
            logger.warning("CAT connect failed for scope-init: %s", e)

    # Check if serial port is actually open (CatController uses _ser)
    serial_port = getattr(cat, '_ser', None) or getattr(cat, 'serial', None)
    if serial_port is None or not getattr(serial_port, 'is_open', False):
        logger.warning("CAT serial port not open — scope-init unavailable")
        return

    logger.info("Sending scope-init CAT commands...")

    # Extended CAT commands to initialize the scope display.
    # These write to the FT-710's internal registers to enable
    # the scope data stream on the FT4222 SPI interface.
    scope_cmds = [
        # Enable scope data output on FT4222 SPI
        # EX = extended command prefix
        "EX040101",
        # Set scope to CENTER mode (not FIX mode)
        "EX040200",
    ]
    for cmd in scope_cmds:
        try:
            await cat.send_command(cmd)
            await asyncio.sleep(0.05)
            logger.debug("Scope-init sent: %s", cmd)
        except Exception as e:
            logger.warning("Scope-init cmd %s error: %s", cmd, e)

    logger.info("Scope-init CAT commands complete")


async def _initial_state_sync():
    """Perform full state read from radio on initial connect."""
    global cat, radio
    if cat is None or not cat.connected:
        return
    logger.info("Performing initial state sync...")
    sync_data = await cat.initial_state_sync()
    new_state = RadioState.from_sync_result(sync_data)
    new_state.serial_connected = True
    # Copy all fields to the global state
    for field_name in vars(new_state):
        if not field_name.startswith('_'):
            setattr(radio, field_name, getattr(new_state, field_name))
    radio.mark_dirty("serial_connected")
    logger.info("Initial state: freq=%d mode=%s s_meter=%d",
                radio.active_freq, radio.mode_name, radio.s_meter)


# ── FastAPI App ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect to FT-710, start polling, scope, and audio.
       Shutdown: disconnect, force RX, cancel tasks."""
    global cat, scheduler, scope, audio, _scope_read_task, _scope_broadcast_task
    global _audio_rx_task, _audio_tx_task, _opus_tx_decoder

    # ── Startup ──
    startup_time = time.time()
    logger.info("FT-710 Web Control starting on port %d", WEB_PORT)
    logger.info("Serial port: %s @ %d baud", SERIAL_PORT, BAUD_RATE)

    cat = CatController(SERIAL_PORT, BAUD_RATE)
    connected = await cat.connect()
    radio.update(serial_connected=connected)

    if connected:
        await _initial_state_sync()
        await _init_scope_cat()
        scheduler = PollScheduler(cat, radio, on_state_changed=_broadcast_state)
        await scheduler.start()
    else:
        logger.warning("Could not connect to radio. Server will serve UI only.")
        logger.warning("Check serial port: %s", SERIAL_PORT)

    # ── Audio handler ──────────────────────────────────────────────
    audio = AudioHandler()
    # Use a thread with timeout — FT-710 USB audio can hang on open
    _audio_ok = False
    _pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    _audio_fut = _pool.submit(audio.start_rx)
    try:
        _audio_ok = _audio_fut.result(timeout=8)
    except concurrent.futures.TimeoutError:
        logger.warning("Audio RX init timed out (8s) — FT-710 USB audio may be unresponsive")
        logger.warning("  Try reconnecting the FT-710 USB cable or power-cycling the radio")
    except Exception as e:
        logger.warning("Audio RX init failed: %s", e)
    finally:
        _pool.shutdown(wait=False)  # Don't block on the hung p.open() thread

    # TX Opus decoder (browser mic → server → radio)
    try:
        _opus_tx_decoder = TxOpusDecoder()
    except Exception as e:
        logger.warning("TX Opus decoder unavailable: %s", e)
        _opus_tx_decoder = None

    # Start audio tasks (skip if audio init failed)
    if _audio_ok:
        _audio_rx_task = asyncio.create_task(_audio_rx_loop(), name="audio_rx")
    _audio_tx_task = asyncio.create_task(_audio_tx_drain_loop(), name="audio_tx")

    # Start scope handler — broadcasts S-meter fallback until real data arrives
    scope = ScopeHandler()
    scope.set_on_frame(_on_scope_frame)
    _scope_broadcast_task = asyncio.create_task(_broadcast_spectrum_loop(), name="scope_bcast")

    # Try to initialize scope via CAT (enables FT4222 SPI output on radio)
    # Do this even if initial CAT probe failed — the serial port may still work
    await _init_scope_cat()

    logger.info("Server ready!")

    yield

    # ── Shutdown ──
    logger.info("Shutting down...")

    # Force RX (safety)
    if cat and cat.connected:
        try:
            await cat.set_ptt(False)
            await asyncio.sleep(0.1)
        except Exception:
            pass

    # Stop audio
    if _audio_rx_task:
        _audio_rx_task.cancel()
    if _audio_tx_task:
        _audio_tx_task.cancel()
    if _opus_tx_decoder:
        try:
            _opus_tx_decoder.close()
        except Exception:
            pass
        _opus_tx_decoder = None
    if audio:
        await asyncio.to_thread(audio.close)
        audio = None

    # Stop scope
    await _stop_scope_pipe()
    if _scope_broadcast_task:
        _scope_broadcast_task.cancel()
    if scope:
        await scope.disconnect()

    if scheduler:
        await scheduler.stop()
    if cat:
        await cat.disconnect()
    logger.info("Server stopped.")


app = FastAPI(title="FT-710 Web Control", lifespan=lifespan)

# COOP/COEP middleware for SharedArrayBuffer (future audio worklet support)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Embedder-Policy"] = "credentialless"
    return response


# ── Auth Middleware ──────────────────────────────────────────────────

# Paths that don't require authentication
PUBLIC_PATHS = {"/login", "/api/auth/login", "/favicon.png", "/manifest.json", "/sw.js"}
# WebSocket paths: must NOT be redirected — WebSocket can't follow 302.
# Let the WS handler check auth and close with proper code 4001.
WS_PATHS = {"/WSradio", "/WSspectrum", "/WSaudioRX", "/WSaudioTX"}

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Protect all routes except public paths, static assets, and login."""
    path = request.url.path

    # Allow static assets and public paths
    if path in PUBLIC_PATHS or path.startswith("/static"):
        return await call_next(request)

    # Allow login API
    if path == "/api/auth/login":
        return await call_next(request)

    # WebSocket paths: pass through (WS handlers send code 4001 on auth failure
    # so the browser's handleAuthExpired() can act on it properly).
    if path in WS_PATHS:
        return await call_next(request)

    # Check auth
    if not _verify_auth(request):
        if path.startswith("/api/"):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        # Redirect to login
        next_url = request.url.path + ("?" + request.url.query if request.url.query else "")
        return RedirectResponse(f"/login?next={next_url}", status_code=302)

    return await call_next(request)


# ── Login Routes ────────────────────────────────────────────────────

@app.get("/login", include_in_schema=False)
async def login_page(request: Request):
    """Serve the login page."""
    login_html = STATIC_DIR / "login.html"
    if login_html.exists():
        return HTMLResponse(login_html.read_text(encoding="utf-8"))
    return HTMLResponse("""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport"
    content="width=device-width,initial-scale=1"><title>FT-710 Login</title>
    <style>body{font-family:-apple-system,sans-serif;background:#1a1a1a;color:#eee;
    display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;}
    form{background:#2a2a2a;padding:2rem;border-radius:12px;width:300px}
    h1{text-align:center;color:#f59e0b;margin:0 0 1rem}
    input{width:100%;padding:12px;margin:8px 0;border:1px solid #444;border-radius:8px;
    background:#333;color:#fff;font-size:16px;box-sizing:border-box}
    button{width:100%;padding:12px;margin-top:12px;background:#f59e0b;color:#000;
    border:none;border-radius:8px;font-size:16px;font-weight:bold;cursor:pointer}
    .error{color:#ff4444;margin-top:8px;text-align:center}</style></head>
    <body><form id="loginForm"><h1>FT-710</h1>
    <input type="password" id="password" placeholder="Password" autofocus required>
    <button type="submit">Login</button><div class="error" id="error"></div></form>
    <script>
    document.getElementById('loginForm').onsubmit=async function(e){e.preventDefault();
    var p=document.getElementById('password').value;try{var r=await fetch('/api/auth/login',
    {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:p})});
    if(r.ok){var n=new URLSearchParams(window.location.search).get('next')||'/';
    window.location.replace(n);}else{document.getElementById('error').textContent='Invalid password';}
    }catch(err){document.getElementById('error').textContent='Connection error';}};
    </script></body></html>
    """, status_code=200)


@app.post("/api/auth/login")
async def api_login(request: Request):
    """Authenticate with password.  Sets auth cookie on success."""
    # Check rate limit
    client_ip = request.client.host if request.client else "unknown"
    if not _check_login_rate_limit(client_ip):
        logger.warning("Rate limit exceeded for login from IP: %s", client_ip)
        return JSONResponse({"error": "Too many login attempts. Please try again later."}, status_code=429)
    
    try:
        body = await request.json()
        password = body.get("password", "")
    except Exception:
        password = ""

    if password != WEB_PASSWORD:
        return JSONResponse({"error": "Invalid password"}, status_code=401)

    # Password strength validation (only on first login)
    if len(password) < 12:
        logger.warning("Weak password detected! Use at least 12 characters with mixed case, numbers, and symbols.")

    token = _make_auth_token()
    _auth_tokens.add(token)

    response = JSONResponse({"ok": True, "token": token})
    response.set_cookie(
        AUTH_COOKIE, token,
        max_age=30 * 24 * 3600,  # 30 days
        httponly=False,          # JS needs to read it for WebSocket
        samesite="lax",
    )
    return response


@app.post("/api/auth/logout")
async def api_logout(request: Request):
    """Invalidate the session token."""
    token = request.cookies.get(AUTH_COOKIE)
    if token:
        _auth_tokens.discard(token)
    response = JSONResponse({"ok": True})
    response.delete_cookie(AUTH_COOKIE)
    return response


@app.get("/api/auth/check")
async def api_auth_check(request: Request):
    """Check if the current session is valid."""
    if _verify_auth(request):
        return JSONResponse({"authenticated": True})
    return JSONResponse({"authenticated": False}, status_code=401)


# ── Status API ──────────────────────────────────────────────────────

@app.get("/api/status")
async def api_status():
    """Return full radio state as JSON."""
    return JSONResponse(radio.to_dict())


# ── Health Check API ──────────────────────────────────────────────

@app.get("/api/health")
async def api_health():
    """Health check endpoint for monitoring/proxy setups."""
    import time as _time
    health_status = {
        "status": "healthy",
        "radio_connected": cat.connected if cat else False,
        "audio_available": audio is not None and audio._rx_running if audio else False,
        "scope_connected": scope.connected if scope else False,
        "uptime_seconds": _time.time() - startup_time if 'startup_time' in globals() else 0,
    }
    
    # Check if any critical components are down
    if not health_status["radio_connected"]:
        health_status["status"] = "degraded"
        health_status["message"] = "Radio not connected"
    
    return JSONResponse(health_status)


# ── Memory Channels API ─────────────────────────────────────────────

@app.get("/api/mem_channels")
async def api_get_mem_channels():
    """Return memory channels."""
    return JSONResponse({"channels": _load_mem_channels()})


@app.post("/api/mem_channels")
async def api_post_mem_channels(request: Request):
    """Save memory channels."""
    try:
        body = await request.json()
        channels = body.get("channels", [])
        _save_mem_channels(channels)
        await _broadcast_mem_channels()
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# ── WebSocket Endpoint ──────────────────────────────────────────────

@app.websocket("/WSradio")
async def ws_radio(ws: WebSocket):
    """Main control WebSocket.  Handles all real-time radio state and commands."""
    # Check auth via query param (browser WebSocket doesn't support custom headers)
    token = ws.query_params.get("token", "")
    if not token or token not in _auth_tokens:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()
    ctrl_clients.add(ws)
    logger.info("WS client connected (%d total)", len(ctrl_clients))
    if scheduler:
        scheduler.set_active(len(ctrl_clients) > 0)

    # Push full initial state
    try:
        channels = _load_mem_channels()
        await ws.send_text(json.dumps({
            "type": "fullState",
            "data": radio.to_dict(),
            "bands": BANDS,
            "modes": UI_MODES,
            "memChannels": channels,
        }))
    except Exception:
        ctrl_clients.discard(ws)
        return

    try:
        while True:
            msg_str = await ws.receive_text()
            await _handle_ws_message(ws, msg_str)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("WS error: %s", e)
    finally:
        ctrl_clients.discard(ws)
        logger.info("WS client disconnected (%d remain)", len(ctrl_clients))
        if scheduler:
            scheduler.set_active(len(ctrl_clients) > 0)

        # PTT safety: if no clients remain and radio is transmitting, force RX
        if not ctrl_clients and radio.is_transmitting and cat and cat.connected:
            logger.warning("Last client disconnected during TX! Forcing RX.")
            try:
                await cat.set_ptt(False)
                radio.update(tx_status=0)
            except Exception:
                pass
            if audio:
                await asyncio.to_thread(audio.stop_tx)


# ── Spectrum WebSocket ───────────────────────────────────────────────

@app.websocket("/WSspectrum")
async def ws_spectrum(ws: WebSocket):
    """Binary spectrum data endpoint.  Sends waterfall rows at ~30 fps.

    Format: 1-byte version (0x01) + 850 bytes wf1 spectrum + 850 bytes wf2.
    Total: 1701 bytes per frame.
    """
    token = ws.query_params.get("token", "")
    if not token or token not in _auth_tokens:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()
    spectrum_clients.add(ws)
    logger.info("Spectrum client connected (%d total)", len(spectrum_clients))
    await _ensure_scope_pipe_running()
    try:
        while True:
            # Keep connection alive, actual data sent by broadcast loop
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        spectrum_clients.discard(ws)
        logger.info("Spectrum client disconnected (%d remain)", len(spectrum_clients))
        if not spectrum_clients:
            await _stop_scope_pipe()


# ── Audio RX WebSocket ────────────────────────────────────────────────

@app.websocket("/WSaudioRX")
async def ws_audio_rx(ws: WebSocket):
    """RX audio stream endpoint. Sends tagged binary frames:
    1-byte codec tag (0x00=PCM, 0x01=Opus) + payload.

    Data is produced by the _audio_rx_loop and broadcast to all
    connected audio_rx_clients.
    """
    token = ws.query_params.get("token", "")
    if not token or token not in _auth_tokens:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()
    audio_rx_clients.add(ws)
    logger.info("Audio RX client connected (%d total)", len(audio_rx_clients))
    try:
        while True:
            await ws.receive()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        audio_rx_clients.discard(ws)
        logger.info("Audio RX client disconnected (%d remain)", len(audio_rx_clients))


# ── Audio TX WebSocket ────────────────────────────────────────────────

@app.websocket("/WSaudioTX")
async def ws_audio_tx(ws: WebSocket):
    """TX mic uplink endpoint. Receives binary frames:
    1-byte codec tag (0x00=PCM, 0x01=Opus) + payload.
    Text frames: 'm:rate,...' for settings, 's:' for stop.

    Single-owner: only the first connected client's audio is fed to the
    radio; subsequent clients connect but their frames are ignored until
    the owner disconnects.
    """
    global audio, _opus_tx_decoder, _tx_owner_ws

    token = ws.query_params.get("token", "")
    if not token or token not in _auth_tokens:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws.accept()
    audio_tx_clients.add(ws)
    is_owner = _tx_owner_ws is None
    if is_owner:
        _tx_owner_ws = ws
    logger.info("Audio TX client connected (%d total, owner=%s)",
                len(audio_tx_clients), is_owner)

    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break

            if "bytes" in msg and msg["bytes"] is not None:
                # Only the owner's audio reaches the radio; ignore others.
                if ws is not _tx_owner_ws:
                    continue
                data = msg["bytes"]
                if len(data) < 2:
                    continue

                # Decode codec-tagged mic frame → PCM → audio output
                tag = data[0]
                frame = data[1:]

                if tag == AUDIO_TAG_OPUS and _opus_tx_decoder:
                    pcm = _opus_tx_decoder.decode(frame)
                    if pcm and audio:
                        audio.feed_tx_audio(pcm)
                elif tag == AUDIO_TAG_PCM:
                    if audio:
                        audio.feed_tx_audio(frame)
                else:
                    # Legacy: untagged, assume PCM
                    if audio:
                        audio.feed_tx_audio(data)

            elif "text" in msg and msg["text"]:
                text = msg["text"]
                if text.startswith("s:") or text == "stop":
                    # Client stopped capturing. Do NOT clear the queue here —
                    # the PTT-release path drains queued audio before dropping
                    # RF, so word-endings survive. Clearing now would chop
                    # the tail if 's:' arrives before ptt:false.
                    pass
                elif text.startswith("m:"):
                    # Settings: rate, encode, etc.
                    try:
                        parts = text[2:].split(",")
                        # tx_rate = int(float(parts[0])) if parts else 16000
                    except Exception:
                        pass

    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        audio_tx_clients.discard(ws)
        if ws is _tx_owner_ws:
            _tx_owner_ws = None
            # Force RX if the TX-audio owner vanishes while keyed — otherwise
            # the radio sits on a dead carrier until the control socket also
            # drops (dead-man switch) or the user releases PTT.
            if radio.is_transmitting and cat and cat.connected:
                logger.warning("TX audio owner disconnected during TX! Forcing RX.")
                try:
                    await cat.set_ptt(False)
                    radio.update(tx_status=0)
                except Exception:
                    pass
            if audio:
                await asyncio.to_thread(audio.stop_tx)
        logger.info("Audio TX client disconnected (%d remain, owner=%s)",
                    len(audio_tx_clients), _tx_owner_ws is not None)


# ── Static File Serving ─────────────────────────────────────────────

@app.get("/{path:path}")
async def serve_static(path: str, request: Request):
    """Serve static files.  Index.html is served for SPA routes."""
    if not _verify_auth(request) and path not in ("", "login", "favicon.png", "manifest.json", "sw.js"):
        return RedirectResponse("/login")

    file_path = STATIC_DIR / (path if path else "index.html")

    if file_path.is_file():
        # Determine content type
        ext = file_path.suffix.lower()
        content_types = {
            ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
            ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml",
            ".ico": "image/x-icon", ".wav": "audio/wav", ".mp3": "audio/mpeg",
        }
        media_type = content_types.get(ext, "application/octet-stream")
        return FileResponse(file_path, media_type=media_type)

    # Fallback to index.html for SPA routes
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return HTMLResponse("<h1>FT-710</h1><p>Static files not found.</p>", status_code=404)


# ── Entry Point ─────────────────────────────────────────────────────

def main():
    """Parse CLI args and start the server.

    Environment variables are set BEFORE importing the app so that
    config.py picks up the correct values at module load time.
    """
    import argparse
    parser = argparse.ArgumentParser(description="FT-710 Web Control Server")
    parser.add_argument("--port", type=int, default=WEB_PORT, help=f"Web server port (default: {WEB_PORT})")
    parser.add_argument("--serial-port", default=SERIAL_PORT, help=f"Serial port (default: {SERIAL_PORT})")
    parser.add_argument("--baud", type=int, default=BAUD_RATE, help=f"Baud rate (default: {BAUD_RATE})")
    parser.add_argument("--password", default=WEB_PASSWORD, help="Web login password")
    parser.add_argument("--host", default=WEB_HOST, help=f"Bind address (default: {WEB_HOST})")
    parser.add_argument("--ssl-cert", default=SSL_CERTFILE, help=f"SSL cert file (default: {SSL_CERTFILE})")
    parser.add_argument("--ssl-key", default=SSL_KEYFILE, help=f"SSL key file (default: {SSL_KEYFILE})")
    parser.add_argument("--no-ssl", action="store_true", help="Disable SSL (use plain HTTP)")
    args = parser.parse_args()

    # Set env vars BEFORE uvicorn imports the app module
    os.environ["FT710_SERIAL_PORT"] = args.serial_port
    os.environ["FT710_BAUD_RATE"] = str(args.baud)
    os.environ["FT710_WEB_PORT"] = str(args.port)
    os.environ["FT710_WEB_PASSWORD"] = args.password
    os.environ["FT710_WEB_HOST"] = args.host

    # SSL configuration
    ssl_kwargs = {}
    if not args.no_ssl and os.path.exists(args.ssl_cert) and os.path.exists(args.ssl_key):
        ssl_kwargs = {
            "ssl_certfile": args.ssl_cert,
            "ssl_keyfile": args.ssl_key,
        }
        logger.info("SSL enabled: %s", args.ssl_cert)
    else:
        logger.warning("SSL disabled or cert/key not found (cert=%s key=%s)",
                       args.ssl_cert, args.ssl_key)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        reload=False,
        **ssl_kwargs,
    )


if __name__ == "__main__":
    main()
