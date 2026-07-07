#!/usr/bin/env python3
"""
FT-710 Web Control Server
=========================
FastAPI-based web server that bridges a browser to a Yaesu FT-710
radio via serial CAT protocol.  Provides a WebSocket endpoint for
real-time control and state updates, plus REST APIs for memory
channels and authentication.
"""
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
# Single-owner guard for the TX uplink: only the first connected TX client's
# audio is fed to the radio. Prevents two open tabs from interleaving mic
# frames into the same playback queue (garbled TX). A later client takes over
# only after the current owner disconnects.
_tx_owner_ws: Optional[WebSocket] = None
_state_broadcast_task: asyncio.Task | None = None
_scope_read_task: asyncio.Task | None = None
_scope_broadcast_task: asyncio.Task | None = None
_audio_rx_task: asyncio.Task | None = None
_audio_tx_task: asyncio.Task | None = None

# TX Opus decoder (browser mic → server)
_opus_tx_decoder: TxOpusDecoder | None = None

# Auth: valid session tokens (server-side, cleared on restart)
_auth_tokens: set[str] = set()

# Memory channels file
SCRIPT_DIR = Path(__file__).parent
STATIC_DIR = SCRIPT_DIR / "static"
MEM_FILE = SCRIPT_DIR / "mem_channels.json"

# ── Auth Helpers ────────────────────────────────────────────────────

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
            data = json.loads(MEM_FILE.read_text())
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
    MEM_FILE.write_text(json.dumps({"channels": channels[:MEM_CHANNEL_COUNT]}, indent=2))

# ── Broadcast ───────────────────────────────────────────────────────

async def _broadcast_state():
    """Send dirty state fields to all connected WebSocket clients."""
    global ctrl_clients
    dirty = radio.get_and_clear_dirty()
    if not dirty:
        return
    update = {
        "type": "stateUpdate",
        "fields": radio.to_dirty_dict(dirty),
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
    """
    global scope, spectrum_clients
    interval = 1.0 / 30.0
    _first = True
    while True:
        try:
            if scope and spectrum_clients:
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
    global scope
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
                        logger.info("scope_pipe: %s", payload)
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

# ── Audio Broadcast ────────────────────────────────────────────────────

async def _audio_rx_loop():
    """Capture RX audio from the sound card and broadcast to clients.

    Reads int16 PCM chunks from the audio handler, encodes via Opus (or
    sends raw PCM), and broadcasts to all connected audio_rx_clients.

    Runs continuously while the server is active. Each frame is prefixed
    with a 1-byte codec tag so the client knows how to decode.
    """
    global audio, audio_rx_clients
    interval = 0.020  # 20 ms chunk interval
    _first = True
    _loop_count = 0
    _pcm_count = 0
    _send_count = 0
    while True:
        try:
            _loop_count += 1
            if audio and audio._rx_running:
                pcm = audio.read_rx_chunk()
                if pcm:
                    _pcm_count += 1
                    frames = audio.encode_rx_audio(pcm)
                    if frames:
                        _send_count += 1
                        if audio_rx_clients:
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
                            # Send to all clients in parallel — a slow client
                            # (WiFi jitter / TCP backpressure) shouldn't
                            # stall the rest or delay the next audio chunk.
                            async def _send_one(ws):
                                for frame in frames:
                                    await ws.send_bytes(frame)
                            results = await asyncio.gather(
                                *[_send_one(ws) for ws in audio_rx_clients],
                                return_exceptions=True,
                            )
                            dead: set[WebSocket] = set()
                            for ws, res in zip(list(audio_rx_clients), results):
                                if isinstance(res, Exception):
                                    logger.warning("Audio send error (removing client): %s", res)
                                    dead.add(ws)
                            if dead:
                                logger.warning("Removed %d dead audio clients", len(dead))
                            audio_rx_clients -= dead
            # Periodic health log
            if _loop_count % 250 == 0:  # Every 5 seconds
                logger.info("Audio loop: loops=%d pcm_chunks=%d sends=%d clients=%d running=%s",
                           _loop_count, _pcm_count, _send_count,
                           len(audio_rx_clients), audio._rx_running if audio else False)
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
    """
    global audio
    interval = 0.010  # 10 ms drain interval
    while True:
        try:
            if audio:
                await asyncio.to_thread(audio.write_tx_chunk)
        except asyncio.CancelledError:
            return
        except Exception:
            pass
        await asyncio.sleep(interval)


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
            await cat.set_frequency(freq, vfo)
            if vfo == "B":
                radio.update(vfo_b_freq=freq)
            else:
                radio.update(vfo_a_freq=freq)
            scheduler and scheduler.skip_next_poll("if", 1.0)

        elif field == "vfo_a_freq":
            freq = int(value)
            await cat.set_frequency(freq, "A")
            radio.update(vfo_a_freq=freq)
            scheduler and scheduler.skip_next_poll("if", 1.0)

        elif field == "vfo_b_freq":
            freq = int(value)
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
                await cat.set_ptt(True)
                radio.update(tx_status=1)
                if audio:
                    await asyncio.to_thread(audio.start_tx)
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
                             swr_meter=0, comp_meter=0)
            scheduler and scheduler.skip_next_poll("tx_status", 1.0)

        elif field == "tune":
            on = value is True or str(value).lower() == "true"
            if on:
                await cat.set_tune(True)
                radio.update(tx_status=2)
            else:
                await cat.set_tune(False)
                for _ in range(3):
                    await asyncio.sleep(0.2)
                    ptt = await cat.get_ptt()
                    if ptt == 0:
                        break
                    await cat.set_ptt(False)
                radio.update(tx_status=0)
            scheduler and scheduler.skip_next_poll("tx_status", 1.0)

        elif field == "filter" or field == "filter_width":
            idx = int(value)
            await cat.set_filter_width(idx)
            radio.update(filter_width=idx)
            scheduler and scheduler.skip_next_poll("filter_width", 3.0)

        elif field == "af_gain":
            v = max(0, min(255, int(value)))
            await cat.set_af_gain(v)
            radio.update(af_gain=v)
            scheduler and scheduler.skip_next_poll("af_gain", 3.0)

        elif field == "rf_gain":
            v = max(0, min(255, int(value)))
            await cat.set_rf_gain(v)
            radio.update(rf_gain=v)

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
                await cat.set_band_stack(band["bsr"])
                radio.update(vfo_a_freq=band["default_freq"], active_vfo="A")
                scheduler and scheduler.skip_next_poll("if", 1.0)

        elif field == "vfo_equal":
            # A = B: copy VFO-B to VFO-A
            await cat.set_frequency(radio.vfo_b_freq, "A")
            radio.update(vfo_a_freq=radio.vfo_b_freq)
            scheduler and scheduler.skip_next_poll("if", 1.0)

        elif field == "vfo_swap":
            # Swap VFO-A and VFO-B
            fa = radio.vfo_a_freq
            fb = radio.vfo_b_freq
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
    logger.info("FT-710 Web Control starting on port %d", WEB_PORT)
    logger.info("Serial port: %s @ %d baud", SERIAL_PORT, BAUD_RATE)

    cat = CatController(SERIAL_PORT, BAUD_RATE)
    connected = await cat.connect()
    radio.serial_connected = connected

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

    # Start scope_pipe subprocess for real FT4222 SPI data
    # This runs independently of CAT serial — scope data comes via FT4222 chip
    scope_pipe_path = SCRIPT_DIR / "scope_pipe.py"
    if scope_pipe_path.exists():
        logger.info("Starting scope_pipe subprocess...")
        try:
            scope_proc = await asyncio.create_subprocess_exec(
                sys.executable, str(scope_pipe_path),
                stdout=_subprocess.PIPE, stderr=_subprocess.PIPE,
            )
            _scope_read_task = asyncio.create_task(
                _read_scope_pipe(scope_proc), name="scope_pipe_read"
            )
            logger.info("scope_pipe subprocess started (pid=%d)", scope_proc.pid)
            # NOTE: scope._connected is set by _read_scope_pipe after the
            # first valid frame arrives — we do NOT set it here.
            # Until then, the broadcast loop falls back to S-meter data.
        except Exception as e:
            logger.warning("Failed to start scope_pipe: %s", e)
            logger.warning("Spectrum will use S-meter fallback only")
    else:
        logger.warning("scope_pipe.py not found at %s — spectrum will use S-meter fallback only",
                       scope_pipe_path)

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
    if _scope_read_task:
        _scope_read_task.cancel()
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
        return HTMLResponse(login_html.read_text())
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
    try:
        body = await request.json()
        password = body.get("password", "")
    except Exception:
        password = ""

    if password != WEB_PASSWORD:
        return JSONResponse({"error": "Invalid password"}, status_code=401)

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
            # Force RX on TX owner disconnect (safety)
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
        "server:app",
        host=args.host,
        port=args.port,
        log_level="info",
        reload=False,
        **ssl_kwargs,
    )


if __name__ == "__main__":
    main()
