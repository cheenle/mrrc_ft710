# MRRC FT-710 Test Suite

## Overview

Automated test suite covering the core backend modules. All tests run **without hardware** — no FT-710 radio, no serial port, no USB audio device needed. 160 tests across 10 test modules.

```bash
python -m unittest discover -s tests -v
```

## Test Results Summary

| Metric | Value |
|--------|-------|
| Total tests | 160 |
| Passed | 158 |
| Skipped | 2 (fastapi not in test env) |
| Failed | 0 |
| Execution time | ~0.01s |

## Test Modules

### 1. test_radio_state.py — RadioState (28 tests)

SDD coverage: §7.2, AD-003, §9.7

| Class | Tests | Covers |
|-------|-------|--------|
| `RadioStateFieldMutationTests` | 7 | Field updates, dirty tracking, unknown field handling, batch mutation |
| `RadioStateDerivedPropertiesTests` | 13 | active_freq, mode_name, band_name, is_transmitting, s_meter_dbm, s_unit, preamp_label, attenuator_label |
| `RadioStateSerializationTests` | 5 | to_dict (core + derived), to_dirty_dict, value accuracy |
| `RadioStateFromSyncResultTests` | 6 | CAT response parsing, empty data, malformed data, booleans, preamp/att, tuner |

### 2. test_cat_controller.py — CAT Protocol (24 tests)

SDD coverage: AD-002, §9.6, §10.4

| Class | Tests | Covers |
|-------|-------|--------|
| `CatCommandFormattingTests` | 16 | FA, FB, MD0, TX, SM0, SH0, AG, PC, PA0, RA0, NB0, NR0, BC, PR, PS, ST, VS, SS, AC, BS — all command formats |
| `CatResponseParsingTests` | 5 | Frequency parse, S-meter parse, mode parse, PTT parse, IF response parse, error detection |
| `CatControllerMockedTests` | 5 | Command terminator (;), query vs set, ASCII encoding, triple PTT verify sequence |

### 3. test_config.py — Configuration Tables (25 tests)

SDD coverage: §7.2, §10.4, NFRs

| Class | Tests | Covers |
|-------|-------|--------|
| `ModeTableTests` | 5 | Mode name↔num mapping, bidirectional lookup, display names, UI_MODES |
| `BandTableTests` | 6 | Band list structure, get_band_for_frequency (20m/40m/80m/10m/edge cases) |
| `FilterTableTests` | 5 | Filter widths by mode (SSB, CW, FM), get_filter_hz |
| `SMeterCalibrationTests` | 4 | raw_to_dbm monotonic, raw_to_s_unit labels (S0–S9, +10–+60) |
| `ConfigConstantsTests` | 5 | PREAMP_LABELS, ATTENUATOR_LABELS, SCOPE_SPANS, MEM_CHANNEL_COUNT, AUTH_CONFIG |

### 4. test_audio.py — Audio Handler + Opus Codec (20 tests)

SDD coverage: AD-004, NFR-060–NFR-065

| Class | Tests | Covers |
|-------|-------|--------|
| `CodecTagTests` | 4 | AUDIO_TAG_PCM (0x00), AUDIO_TAG_OPUS (0x01), tag distinctness, 1-byte fit |
| `OpusConstantsTests` | 6 | RX_RATE=48000, FRAME_SAMPLES=960, DEFAULT_BITRATE=64000, MIN=8000, MAX=128000 |
| `AudioFramingTests` | 6 | Tagged PCM frame format, tagged Opus frame format, Int16 range, 768kbps PCM bandwidth, multi-frame tags |
| `AudioDeviceDetectionTests` | 2 | FT-710 name pattern matching, non-FT-710 rejection |

### 5. test_server_ws_protocol.py — WebSocket Protocol (26 tests)

SDD coverage: §9.2, §10.4, §15

| Class | Tests | Covers |
|-------|-------|--------|
| `WSMessageFormatTests` | 12 | fullState, stateUpdate, set, get, ping/pong, error, memChannels, memSave, value, legacy colon format |
| `WSAuthTests` | 4 | Token format (64 hex chars), valid/invalid token check, WS close code 4001 |
| `PTTSafetyLogicTests` | 8 | TX1/TX0 commands, triple verify, dead-man switch (3 conditions), watchdog retry count, sendBeacon format, tx audio stop signal, m: settings format |
| `StateBroadcastLogicTests` | 5 | Empty dirty set skip, partial update, dirty clear after broadcast, skip_next_poll |

### 6. test_poll_scheduler.py — Poll Scheduler (12 tests)

SDD coverage: AD-009, §9.6

| Class | Tests | Covers |
|-------|-------|--------|
| `PollTierStructureTests` | 6 | 5-tier intervals (100ms/500ms/2s/5s), tier commands, throughput limit |
| `PollSkipLogicTests` | 4 | Skip field accumulation, expiry, multi-field skip, duration types |
| `PollingOrderTests` | 2 | User command priority over poll, resume after skip expiry |

### 7. test_scope_frame.py — Scope Frame Parsing (8 tests)

SDD coverage: AD-005, AD-006, §9.5

| Class | Tests | Covers |
|-------|-------|--------|
| `ScopeFrameTests` | 3 | Parse validation (sync + metadata), sync rejection, pipe payload round-trip |
| `FrameQualityTests` | 4 | All-zero spectrum, all-ones spectrum, normal spectrum metrics (nonzero_pct, dynamic_range) |

### 8. test_radio_state_scope.py — Scope Fields in State (1 test)

SDD coverage: §7.2 (ScopeFrame entity)

### 9. test_scope_handler_fallback.py — S-Meter Fallback (1 test)

SDD coverage: AD-006, §9.5.2

### 10. test_scope_runtime_config.py — SPI Clock Config (2 tests)

SDD coverage: AD-005, §12.2

### 11. test_server_scope_init.py — Scope CAT Init (2 tests, skipped)

SDD coverage: AD-005, §9.5.1

Skipped when `fastapi` is not installed in the test environment. Requires `pip install fastapi` to run.

## Test Coverage by SDD Requirement

| SDD Section | Test Module(s) | Status |
|-------------|---------------|--------|
| AD-001 FastAPI/Uvicorn | test_server_scope_init | Skipped (needs fastapi) |
| AD-002 Direct Serial CAT | test_cat_controller | 24 tests |
| AD-003 Dirty-Field Broadcasting | test_radio_state, test_server_ws_protocol | 33 tests |
| AD-004 Dual-Codec Audio | test_audio | 20 tests |
| AD-005 scope_pipe Subprocess | test_scope_frame, test_scope_runtime_config, test_server_scope_init | 10 tests |
| AD-006 Dual-Mode Spectrum | test_scope_frame, test_scope_handler_fallback | 9 tests |
| AD-007 PTT Safety | test_server_ws_protocol (PTTSafetyLogicTests) | 8 tests |
| AD-008 PyAudio Detection | test_audio (AudioDeviceDetectionTests) | 2 tests |
| AD-009 5-Tier Polling | test_poll_scheduler | 12 tests |
| AD-010 Memory Channels | test_server_ws_protocol (mem messages) | 3 tests |
| §7.2 RadioState Entity | test_radio_state | 28 tests |
| §7.2 Config Tables | test_config | 25 tests |
| §9.2 WS Protocol | test_server_ws_protocol (WSMessageFormatTests) | 12 tests |
| §9.6 Polling | test_poll_scheduler | 12 tests |
| §15 PTT Safety | test_server_ws_protocol (PTTSafetyLogicTests) | 8 tests |
| NFR-060–065 Audio Quality | test_audio | 20 tests |
| NFR-020–023 Auth/Security | test_server_ws_protocol (WSAuthTests) | 4 tests |

## Running Specific Tests

```bash
# All tests
python -m unittest discover -s tests -v

# Single module
python -m unittest tests.test_radio_state -v

# Single test class
python -m unittest tests.test_radio_state.RadioStateFieldMutationTests -v

# Single test method
python -m unittest tests.test_config.ModeTableTests.test_bidirectional_mode_mapping -v
```

## Design Principles

1. **No hardware required**: All tests use mocked serial, no FT-710, no USB audio, no SPI.
2. **Fast execution**: ~160 tests in 0.01s — can run on every commit.
3. **Coverage by SDD**: Each test references the SDD requirement it validates.
4. **Isolation**: Each test is self-contained; no shared mutable state.
5. **Readable failures**: Assertion messages clearly state expected vs actual.
