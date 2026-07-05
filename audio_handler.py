"""
FT-710 Audio Handler
====================
Captures RX audio from the FT-710's USB audio device and streams it
via Opus to the browser. Receives TX audio from the browser and plays
it to the FT-710's USB audio device.

Uses PyAudio for sound card I/O and libopus for compression.
"""

import asyncio
import logging
import time
from collections import deque
from typing import Optional

import numpy as np

from opus_rx import RxOpusEncoder, AUDIO_TAG_PCM, AUDIO_TAG_OPUS, DEFAULT_BITRATE

logger = logging.getLogger("ft710.audio")

# ── PyAudio ────────────────────────────────────────────────────────────
try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    pyaudio = None
    logger.warning("PyAudio not available — audio disabled. Install: pip install pyaudio")

# ── Audio Config ───────────────────────────────────────────────────────
RX_SAMPLE_RATE = 48000       # Capture at 48 kHz
RX_CHUNK_SIZE = 960          # 20 ms @ 48 kHz (matches Opus frame)
RX_CHANNELS = 1
TX_SAMPLE_RATE = 48000       # Playback at 48 kHz
TX_CHANNELS = 1


class AudioHandler:
    """Captures RX audio from sound card and encodes via Opus.
    Receives TX audio (decoded PCM) and plays to sound card."""

    def __init__(self,
                 rx_device_index: Optional[int] = None,
                 tx_device_index: Optional[int] = None):
        self.rx_device = rx_device_index
        self.tx_device = tx_device_index
        self._pa: Optional["pyaudio.PyAudio"] = None
        self._rx_stream: Optional["pyaudio.Stream"] = None
        self._tx_stream: Optional["pyaudio.Stream"] = None
        self._rx_running = False
        self._tx_queue: deque = deque()  # Queue of int16 PCM bytes to play

        # Opus encoder for RX audio
        self.opus_enabled = True
        self.opus_encoder: Optional[RxOpusEncoder] = None
        try:
            self.opus_encoder = RxOpusEncoder(bitrate=DEFAULT_BITRATE)
        except Exception as e:
            logger.warning("Opus encoder unavailable, RX stays on Int16 PCM: %s", e)
            self.opus_enabled = False

        if HAS_PYAUDIO:
            self._init_pyaudio()

    def _init_pyaudio(self):
        """Initialize PyAudio and list available devices."""
        try:
            self._pa = pyaudio.PyAudio()
            logger.info("PyAudio initialized. Available devices:")
            for i in range(self._pa.get_device_count()):
                info = self._pa.get_device_info_by_index(i)
                logger.info(
                    "  [%d] %s (in=%d, out=%d, rate=%d)",
                    i, info['name'],
                    info.get('maxInputChannels', 0),
                    info.get('maxOutputChannels', 0),
                    int(info.get('defaultSampleRate', 0)),
                )
        except Exception as e:
            logger.error("PyAudio init failed: %s", e)
            self._pa = None

    # ── RX: Capture from sound card → Opus frames ──────────────────

    def _find_rx_device(self) -> Optional[int]:
        """Find a suitable input device. Tries the explicit device first,
        then falls back to any device with input channels."""
        if self.rx_device is not None:
            return self.rx_device
        if self._pa is None:
            return None
        # Try to find a device with "FT-710" or "USB Audio" in the name
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0:
                name = info.get('name', '')
                if 'FT-710' in name or 'FT710' in name or 'YAESU' in name.upper():
                    logger.info("Found FT-710 audio input: [%d] %s", i, name)
                    return i
        # Fallback: first device with input channels
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0:
                logger.info("Using default audio input: [%d] %s", i, info.get('name', ''))
                return i
        return None

    def start_rx(self) -> bool:
        """Start capturing RX audio from the sound card."""
        if self._rx_running:
            return True
        if self._pa is None:
            logger.warning("PyAudio not available — cannot start RX")
            return False

        dev = self._find_rx_device()
        if dev is None:
            logger.warning("No audio input device found")
            return False

        try:
            self._rx_stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=RX_CHANNELS,
                rate=RX_SAMPLE_RATE,
                input=True,
                input_device_index=dev,
                frames_per_buffer=RX_CHUNK_SIZE,
                stream_callback=None,  # We'll read in the asyncio loop
            )
            self._rx_running = True
            dev_info = self._pa.get_device_info_by_index(dev)
            logger.info("RX audio started: [%d] %s @ %d Hz",
                        dev, dev_info.get('name', ''), RX_SAMPLE_RATE)
            return True
        except Exception as e:
            logger.error("Failed to start RX audio: %s", e)
            return False

    def stop_rx(self):
        """Stop RX audio capture."""
        self._rx_running = False
        if self._rx_stream:
            try:
                self._rx_stream.stop_stream()
                self._rx_stream.close()
            except Exception:
                pass
            self._rx_stream = None

    def read_rx_chunk(self) -> Optional[bytes]:
        """Read one chunk of int16 PCM audio from the RX stream.
        Non-blocking — uses get_read_available() to check before read.
        Returns None if not enough data is available."""
        if not self._rx_running or self._rx_stream is None:
            return None
        try:
            # Use get_read_available to check, then read what's there
            count = self._rx_stream.get_read_available()
            if count >= RX_CHUNK_SIZE:
                # Read one chunk's worth, or at most 4 chunks to prevent lag
                to_read = min(count, RX_CHUNK_SIZE * 4)
                data = self._rx_stream.read(to_read, exception_on_overflow=False)
                if data and len(data) >= 2:
                    return data
        except OSError as e:
            if "Stream not open" in str(e) or "No such device" in str(e):
                logger.warning("RX stream lost — attempting restart")
                self._rx_running = False
                try: self.stop_rx()
                except Exception: pass
                time.sleep(0.5)
                self.start_rx()
            else:
                logger.debug("RX read error: %s", e)
        except Exception as e:
            logger.debug("RX read error: %s", e)
        return None

    def encode_rx_audio(self, pcm: bytes) -> list[bytes]:
        """Encode RX PCM audio into tagged WebSocket frames.
        Returns list of bytes, each prefixed with codec tag byte."""
        if len(pcm) < 64:
            return []

        frames: list[bytes] = []
        if self.opus_enabled and self.opus_encoder is not None:
            try:
                for pkt in self.opus_encoder.push(pcm):
                    frames.append(bytes([AUDIO_TAG_OPUS]) + pkt)
            except Exception as e:
                logger.warning("Opus encode failed, sending PCM: %s", e)
                frames = [bytes([AUDIO_TAG_PCM]) + pcm]
        else:
            frames = [bytes([AUDIO_TAG_PCM]) + pcm]
        return frames

    # ── TX: Receive from browser → play to sound card ───────────────

    def _find_tx_device(self) -> Optional[int]:
        """Find a suitable output device."""
        if self.tx_device is not None:
            return self.tx_device
        if self._pa is None:
            return None
        # Try FT-710 USB audio output
        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if info.get('maxOutputChannels', 0) > 0:
                name = info.get('name', '')
                if 'FT-710' in name or 'FT710' in name or 'YAESU' in name.upper():
                    logger.info("Found FT-710 audio output: [%d] %s", i, name)
                    return i
        # Fallback: system default output
        try:
            default = self._pa.get_default_output_device_info()
            if default:
                logger.info("Using default audio output: [%d] %s",
                           default.get('index'), default.get('name', ''))
                return default.get('index')
        except Exception:
            pass
        return None

    def start_tx(self) -> bool:
        """Start TX audio playback stream."""
        if self._pa is None:
            return False

        dev = self._find_tx_device()
        if dev is None:
            logger.warning("No audio output device found for TX")
            return False

        try:
            self._tx_stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=TX_CHANNELS,
                rate=TX_SAMPLE_RATE,
                output=True,
                output_device_index=dev,
                frames_per_buffer=RX_CHUNK_SIZE,
            )
            self._tx_queue.clear()
            dev_info = self._pa.get_device_info_by_index(dev)
            logger.info("TX audio started: [%d] %s @ %d Hz",
                        dev, dev_info.get('name', ''), TX_SAMPLE_RATE)
            return True
        except Exception as e:
            logger.error("Failed to start TX audio: %s", e)
            return False

    def stop_tx(self):
        """Stop TX audio playback."""
        if self._tx_stream:
            try:
                self._tx_stream.stop_stream()
                self._tx_stream.close()
            except Exception:
                pass
            self._tx_stream = None
        self._tx_queue.clear()

    def feed_tx_audio(self, pcm: bytes):
        """Queue TX audio for playback."""
        self._tx_queue.append(pcm)

    def write_tx_chunk(self):
        """Write queued TX audio to the output stream.
        Call this from the asyncio event loop at regular intervals."""
        if self._tx_stream is None or not self._tx_stream.is_active():
            return
        # Drain queued PCM to the output stream
        while self._tx_queue:
            data = self._tx_queue.popleft()
            try:
                self._tx_stream.write(data)
            except Exception as e:
                logger.debug("TX write error: %s", e)
                break

    # ── Cleanup ─────────────────────────────────────────────────────

    def close(self):
        """Stop all streams and release PyAudio."""
        self.stop_rx()
        self.stop_tx()
        if self.opus_encoder:
            try:
                self.opus_encoder.close()
            except Exception:
                pass
            self.opus_encoder = None
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None
        logger.info("Audio handler closed")
