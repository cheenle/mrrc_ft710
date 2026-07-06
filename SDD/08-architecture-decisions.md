# 8. Architecture Decisions (ART 0513)

## AD-001: Use FastAPI/Uvicorn for MRRC FT-710 Server

| Attribute | Value |
|-----------|-------|
| Type | Architectural |
| Status | Implemented |
| Decision | Use FastAPI with native WebSocket routes and Uvicorn runtime |

**Problem**: The server needs static file serving, 4 WebSocket endpoints, async serial CAT I/O, scope subprocess management, audio streaming, and auth — all in one process.

**Rationale**: FastAPI/Uvicorn provides direct async integration, lifespan management, middleware, and a small code surface. No Tornado, Flask, or Django needed.

**Consequences**: All server logic lives in `server.py` with modular imports from sibling modules. Lifecycle managed via `@asynccontextmanager lifespan`.

## AD-002: Direct Serial CAT — No Hamlib/Rigctld

| Attribute | Value |
|-----------|-------|
| Type | Architectural |
| Status | Implemented |
| Decision | Use `pyserial` (sync API) with `asyncio.to_thread()` for serial I/O |

**Problem**: Hamlib adds a large dependency and another process to manage. FT-710 CAT protocol is well-documented (Yaesu standard) and straightforward.

**Rationale**: A dedicated `CatController` class with an `asyncio.Lock` for serialized access and thread-pool offloading is simpler, more debuggable, and has fewer failure modes than Hamlib/rigctld.

**Consequences**: The codebase is FT-710 specific. Adding another radio model requires a new commander class.

## AD-003: Dirty-Field State Broadcasting

| Attribute | Value |
|-----------|-------|
| Type | Design |
| Status | Implemented |
| Decision | `RadioState` dataclass tracks changed fields via `_dirty_fields` set; broadcast only changed fields |

**Problem**: Full state broadcasts on every poll would be wasteful (~44 fields at 10Hz).

**Rationale**: `RadioState.update()` records which fields changed; `to_dirty_dict()` sends only those fields. Clients merge partial updates into their local state.

**Consequences**: `stateUpdate` messages are compact; clients must maintain local state mirror.

## AD-004: Tagged Dual-Codec Audio Transport (Opus + Int16 PCM)

| Attribute | Value |
|-----------|-------|
| Type | Architectural |
| Status | Implemented |
| Decision | Both `/WSaudioRX` and `/WSaudioTX` carry a 1-byte codec tag per frame: `0x00` = Int16 PCM, `0x01` = Opus. RX: 48kHz @ 64kbps (fullband, transparent for broadcast music). TX: 48kHz @ 28kbps CBR (voice-optimized, VBR/FEC/DTX/HPF disabled). Default Opus; falls back to PCM. |

**Problem**: (RX) Int16 PCM at 48kHz mono costs ~768kbps — heavy on mobile/WiFi. Opus at 64kbps cuts that 12×. (TX) Browser mic Opus encoding saves uplink bandwidth. A per-frame tag removes negotiation races — receiver inspects tag and decodes accordingly.

**Rationale**: `opus_rx.py` (copied from sunmrrc) provides direct ctypes libopus bindings. Uses `max_data_bytes` cap on `opus_encode()` to control bitrate — avoids arm64 variadic `opus_encoder_ctl` issues. Browser uses WASM `OpusDecoder`/`OpusEncoder`. TX encoder configured for voice: complexity=3 (real-time), VBR=OFF (stable packet size), FEC=OFF (WebSocket TCP), DTX=OFF (no priming gaps), HPF=OFF (preserve low-end).

**Consequences**: Adds libopus dependency (optional — degrades gracefully to PCM). Codec is user-switchable. `AUDIO_TAG_PCM` / `AUDIO_TAG_OPUS` are constants in both Python and JavaScript.

## AD-005: scope_pipe as Standalone Subprocess

| Attribute | Value |
|-----------|-------|
| Type | Architectural |
| Status | Implemented |
| Decision | FT4222 SPI I/O runs in a separate Python process (`scope_pipe.py`), communicating with the server via stdout/stderr pipes |

**Problem**: FT4222 ctypes calls are blocking and can hang. Running them in the asyncio event loop would stall the entire server. Threading is fragile with FTDI D2XX driver state.

**Rationale**: A subprocess isolates the FTDI driver. If scope_pipe crashes, the server continues (falls back to S-meter). Frame format: 4-byte BE uint32 length + payload. stderr carries machine-parseable `STATUS:` lines for diagnostics. Heartbeat frames (len=0) keep pipe alive when idle.

**Consequences**: scope_pipe is independently restartable. Server handles pipe exit gracefully (marks scope disconnected, switches to fallback). Two process lifecycle to manage.

## AD-006: Dual-Mode Spectrum (FT4222 + S-Meter Fallback)

| Attribute | Value |
|-----------|-------|
| Type | Design |
| Status | Implemented |
| Decision | When FT4222 is available, broadcast real 850-point FFT data. When unavailable, generate synthetic multi-peak Gaussian spectrum from CAT S-meter readings |

**Problem**: FT4222 requires specific libraries, D2XX driver config, and exclusive device access. It's not always available.

**Rationale**: The S-meter fallback provides useful visual context (shows band activity) even without hardware scope. The binary frame format is identical in both modes — clients don't care about the source.

**Consequences**: `ScopeHandler` has two code paths: `update_from_scope_frame()` (real data) and `update_from_radio_state()` (synthetic). `scope._connected` flag determines which is active.

## AD-007: PTT Release as Safety-Critical Flow

| Attribute | Value |
|-----------|-------|
| Type | Safety |
| Status | Implemented |
| Decision | Multiple independent release paths: normal WebSocket command, triple TX0 verify, PTT watchdog, dead-man switch on WS disconnect, beforeunload beacon, pagehide handler |

**Problem**: A lost or unprocessed PTT release command can leave the radio transmitting indefinitely — a serious safety and regulatory issue.

**Rationale**: Release is more safety-critical than keying. Each layer catches a different failure mode: lost WS message, half-open socket, browser crash, tab close, app switch. See Chapter 15 for detailed PTT Safety Architecture.

**Consequences**: Frontend PTT logic is more complex; server-side release verification adds ~600ms of TX; polling skip-on-PTT ensures state consistency.

## AD-008: PyAudio Auto-Detection of FT-710 USB Audio

| Attribute | Value |
|-----------|-------|
| Type | Design |
| Status | Implemented |
| Decision | Multi-layer device selection: (1) explicit `FT710_AUDIO_RX_DEVICE`/`FT710_AUDIO_TX_DEVICE` env var (index or name substring), (2) name match for "FT-710"/"FT710"/"YAESU", (3) mono-channel heuristic (FT-710 USB audio has 1 input channel vs typical stereo USB mics), (4) full-duplex heuristic for TX (device with both input + output), (5) system default fallback |

**Problem**: The FT-710 USB audio device name varies by OS and driver version. Hardcoding a device index is fragile. Previous version only searched by name substring and fell back to first input device — could select webcam mic instead of FT-710.

**Rationale**: Name-based matching is more robust than index-based. The mono-channel heuristic is reliable: FT-710 provides exactly 1 input channel (mono RX), while webcams and USB mics typically offer 2 (stereo). Full-duplex preference for TX ensures the same device is used for both RX and TX paths. Logs all available devices at startup for debugging.

**Consequences**: Audio may still use wrong device if multiple mono USB audio devices are present. Configurable device override via env vars is the recommended approach for such setups.

## AD-009: 5-Tier Adaptive Polling

| Attribute | Value |
|-----------|-------|
| Type | Design |
| Status | Implemented |
| Decision | Background CAT polling organized into 5 tiers at 100ms/500ms/2s/5s intervals, with adaptive skip-on-command |

**Problem**: Polling too fast floods the serial port; too slow makes the UI feel unresponsive. Some fields (S-meter) change rapidly; others (filter width) rarely.

**Rationale**: Tier 1 (100ms): freq + mode + S-meter — high churn. Tier 2 (500ms): TX meters (ALC/PWR/SWR) + PTT status. Tier 3 (2s): gains, filter, NR, NB, etc. Tier 4 (5s): Id, Vd, compressor. User commands skip the next poll for that field to avoid redundant queries. Total throughput ~296 bytes/sec at 38400 baud.

**Consequences**: `PollScheduler` manages complex timer state. `skip_next_poll()` called after each user command. CAT errors (timeout, ? response) handled per-command.

## AD-010: Memory Channels as Server-Side JSON

| Attribute | Value |
|-----------|-------|
| Type | Design |
| Status | Implemented |
| Decision | Memory channels stored server-side in `mem_channels.json`; API: GET/POST `/api/mem_channels`; auto-broadcast to all clients on change |

**Problem**: Client-side-only storage loses channels across devices/browsers. Server-side persistence ensures all clients see the same channels.

**Rationale**: Simple JSON file is adequate for 6-99 channel slots. No database needed. Auto-broadcast keeps all clients in sync.

**Consequences**: Channels survive server restarts. File is human-editable. No per-user channel isolation (single shared-password model).

## AD-011: Unified 48kHz TX Audio Pipeline

| Attribute | Value |
|-----------|-------|
| Type | Design |
| Status | Implemented |
| Decision | TX audio chain runs entirely at 48 kHz: browser `getUserMedia({sampleRate:48000})` → Opus encode at 48 kHz (960-sample frames) → server `TxOpusDecoder` at 48 kHz → PyAudio playback at 48 kHz. No sample-rate conversion anywhere in the TX path. |

**Problem**: V1.0 captured mic audio at 16 kHz (320 samples/20ms frame) but PyAudio played back at 48 kHz (expecting 960 samples/20ms). The 3:1 rate mismatch caused the output stream to underrun — every 20ms Opus frame produced 320 samples that filled only 1/3 of the 960-sample playback buffer. The remaining 2/3 was stale/residual buffer data, producing audible crackling ("咔咔咔") on transmitted audio.

**Rationale**: Eliminating the sample-rate conversion eliminates the underrun. Opus at 48 kHz with 28 kbps CBR encodes voice-quality audio — the codec internally allocates bits to the speech band regardless of the nominal sample rate. Browser `getUserMedia` at 48 kHz works on all modern platforms (iOS 15+, Chrome, Firefox). The FT-710 USB audio interface natively operates at 48 kHz.

**Consequences**: Browser mic capture at 48 kHz uses slightly more CPU than 16 kHz (3× sample count), but the encoding cost is dominated by Opus frame processing, not sample count. Opus frames are 960 samples (still 20ms), matching the RX encoder's frame size. PCM fallback path also unified at 48 kHz. `TX_RATE` and `TX_SAMPLE_RATE` are now identical — no future mismatch possible.

## 8.12 Decision Summary

| ID | Topic | Status |
|----|-------|--------|
| AD-001 | FastAPI/Uvicorn backend | Implemented |
| AD-002 | Direct serial CAT (no Hamlib) | Implemented |
| AD-003 | Dirty-field state broadcasting | Implemented |
| AD-004 | Tagged dual-codec audio (Opus + PCM) | Implemented |
| AD-005 | scope_pipe standalone subprocess | Implemented |
| AD-006 | Dual-mode spectrum (FT4222 + fallback) | Implemented |
| AD-007 | PTT release safety flow | Implemented |
| AD-008 | PyAudio FT-710 auto-detection | Implemented |
| AD-009 | 5-tier adaptive polling | Implemented |
| AD-010 | Memory channels as server-side JSON | Implemented |
| AD-011 | Unified 48kHz TX audio pipeline | Implemented |
