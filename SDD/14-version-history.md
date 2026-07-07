# 14. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| SDD V1.2 | 2026-07-08 | Claude | Major bug fixes and performance optimization. **Freq drift fix**: `DN;` is FT-710 active-VFO step-DOWN (~20 Hz), not DNR — removed from settings poll. **Active-VFO tracking**: added VS/FB polling (0.5 s), `freq` web command targets active VFO. **TX meter fix**: FT-710 RM response is 9 chars `RM`+id+6 digits with raw 0-255 in first 3 digits (was `resp[4:]`), added piecewise-linear calibration (Power/SWR/Vd/Id from FT-710.rig). **PTT latency**: 5→3 queries in IF poll, inter-query pause checks, poll timeout 0.25 s, release verify loop removed, TX_DRAIN 150→50 ms. **TX audio**: reverted background start_tx (race with queue-clearing caused SSB zero-power). **RX audio**: removed blocking stderr diagnostic prints (30 fps flush), parallelized WS audio sends via asyncio.gather. **CAT robustness**: AI1 disabled (interfered with FA/MD0/SM0), AI0 sent before ID query. **restart.sh**: fixed `.env` source. Updated gap-analysis doc (DN correction). |
| SDD V1.1 | 2026-07-06 | Claude | Bug fix: TX audio chain unified to 48 kHz (was 16 kHz mic → 48 kHz playback = crackling). Enhanced `_find_rx_device()` with multi-layer detection (config env var, name match, mono-channel heuristic, full-duplex TX). Enhanced `_find_tx_device()` with same heuristics. `opus_rx.py`: TX_RATE 16k→48k, added TX_FRAME_SAMPLES constant. `tx_opus_worker.js`: FRAME_SIZE 320→960, OpusEncoder 16k→48k. `ft710_main.js`: getUserMedia + AudioContext sampleRate 16k→48k (both main + fallback). TX Opus encoder optimized for voice: CBR 28kbps, VBR/FEC/DTX/HPF disabled. Added SSL CLI args. Event-based power button (mobile-first connect). Added AD-011 (Unified 48kHz TX audio pipeline). AudioContext gain explicitly set to 1.0. iOS unlock oscillator during user gesture. |
| SDD V1.0 | 2026-07-06 | Claude | Initial SDD baseline for MRRC FT-710 codebase. All 15 chapters written from scratch based on current repository state: `server.py`, `cat_controller.py`, `audio_handler.py`, `opus_rx.py`, `radio_state.py`, `poll_scheduler.py`, `scope_handler.py`, `scope_pipe.py`, `config.py`, `static/` (HTML, CSS, JS, modules, worklets, worker). Documents: Full CAT control, FT4222 scope + S-meter fallback, Opus/PCM dual-codec bidirectional audio, AudioWorklet RX playback, TX mic capture, 5-tier polling, dirty-field state broadcasting, session auth, memory channels, PTT safety architecture. |

## Design Baseline Notes

- **Radio**: Yaesu FT-710 superheterodyne transceiver (not an SDR).
- **CAT Protocol**: Direct serial CAT via pyserial — no Hamlib, no rigctld, no TCI.
- **Scope**: FTDI FT4222 SPI chip provides 850-point FFT data. Falls back to synthetic S-meter Gaussian spectrum when unavailable.
- **Audio**: Bidirectional through FT-710's built-in USB audio interface via PyAudio. Opus codec (RX 64kbps, TX 28kbps CBR, both 48kHz) with Int16 PCM fallback. TX chain unified at 48 kHz — no sample-rate mismatch.
- **Auth**: Shared-password session auth (`ft710_auth` cookie, 30-day, `?token=` on WebSocket).
- **PTT Safety**: Client-side PTT watchdog (500ms) + dead-man switch (WS disconnect) + beforeunload beacon + pagehide handler + server-side TX status poll (0.5s).  No TX0 verify loop on release (radio obeys TX0 fire-and-forget).  TX audio drain=50ms.
- **Polling**: 7-tier adaptive (was 5): IF 0.1s (FA/MD0/SM0), VFO 0.5s (VS/FB), TX status 0.5s, TX meters 0.5s (TX only), settings 2s, slow 5s, connection watchdog 1s.  Poll queries use 0.25s timeout to bound serial-lock occupancy.  Inter-query pause checks let user commands preempt.  AI mode disabled; active polling only.
- **Meters**: RM3-8 raw 0-255 values calibrated via piecewise-linear tables from FT-710.rig (Power/SWR/Vd/Id).  Frontend displays watts, SWR ratio, volts, amps — not raw numbers.

## Key Architecture Decisions

| ID | Topic |
|----|-------|
| AD-001 | FastAPI/Uvicorn backend |
| AD-002 | Direct serial CAT (no Hamlib) |
| AD-003 | Dirty-field state broadcasting |
| AD-004 | Tagged dual-codec audio (Opus + PCM) |
| AD-005 | scope_pipe standalone subprocess |
| AD-006 | Dual-mode spectrum (FT4222 + fallback) |
| AD-007 | PTT release safety flow (simplified: no verify loop, 50ms drain) |
| AD-008 | PyAudio FT-710 auto-detection |
| AD-009 | 7-tier adaptive polling with bounded lock occupancy |
| AD-010 | Memory channels as server-side JSON |
| AD-011 | Unified 48kHz TX audio pipeline |
| AD-012 | Active-VFO tracking (VS poll + FB poll — target active VFO on freq set) |
| AD-013 | Meter calibration tables (piecewise-linear from FT-710.rig) |
| AD-014 | AI mode disabled — active polling; DN=step-down not DNR |

*This document follows IBM Team Solution Design (TeamSD) methodology v2.3.2.*
*Document ID: SDD-MRRC-FT710-2026-001*
