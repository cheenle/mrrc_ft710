# 14. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| SDD V1.0 | 2026-07-06 | Claude | Initial SDD baseline for MRRC FT-710 codebase. All 15 chapters written from scratch based on current repository state: `server.py`, `cat_controller.py`, `audio_handler.py`, `opus_rx.py`, `radio_state.py`, `poll_scheduler.py`, `scope_handler.py`, `scope_pipe.py`, `config.py`, `static/` (HTML, CSS, JS, modules, worklets, worker). Documents: Full CAT control, FT4222 scope + S-meter fallback, Opus/PCM dual-codec bidirectional audio, AudioWorklet RX playback, TX mic capture, 5-tier polling, dirty-field state broadcasting, session auth, memory channels, PTT safety architecture. |

## Design Baseline Notes

- **Radio**: Yaesu FT-710 superheterodyne transceiver (not an SDR).
- **CAT Protocol**: Direct serial CAT via pyserial — no Hamlib, no rigctld, no TCI.
- **Scope**: FTDI FT4222 SPI chip provides 850-point FFT data. Falls back to synthetic S-meter Gaussian spectrum when unavailable.
- **Audio**: Bidirectional through FT-710's built-in USB audio interface via PyAudio. Opus codec (64kbps default) with Int16 PCM fallback.
- **Auth**: Shared-password session auth (`ft710_auth` cookie, 30-day, `?token=` on WebSocket).
- **PTT Safety**: 8-layer defense: touch-and-hold UX, triple TX0 verify (3×200ms), PTT watchdog (500ms), dead-man switch (WS disconnect), beforeunload beacon, pagehide handler, server-side forced RX, TX audio stream stop.

## Key Architecture Decisions

| ID | Topic |
|----|-------|
| AD-001 | FastAPI/Uvicorn backend |
| AD-002 | Direct serial CAT (no Hamlib) |
| AD-003 | Dirty-field state broadcasting |
| AD-004 | Tagged dual-codec audio (Opus + PCM) |
| AD-005 | scope_pipe standalone subprocess |
| AD-006 | Dual-mode spectrum (FT4222 + fallback) |
| AD-007 | PTT release safety flow |
| AD-008 | PyAudio FT-710 auto-detection |
| AD-009 | 5-tier adaptive polling |
| AD-010 | Memory channels as server-side JSON |

*This document follows IBM Team Solution Design (TeamSD) methodology v2.3.2.*
*Document ID: SDD-MRRC-FT710-2026-001*
