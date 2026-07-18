# FT710Mobile iOS App — Design Spec

**Date:** 2026-07-11
**Status:** Approved
**Target:** iOS 17.0+, Swift 5.9, XcodeGen

## Overview

Native iOS app for the Yaesu FT-710 amateur radio transceiver. Communicates with the existing Python FastAPI backend (`server.py`) via 4 WebSocket connections. Built by adapting the proven architecture from the SunsdrMobile reference app in the same `FT710Mobile/` directory.

## Architecture

### Data Flow

```
FT710 FastAPI Server (:8888)
  │
  ├─ POST /api/auth/login  ──→ ft710_auth cookie → Keychain
  │
  ├─ /WSradio (JSON) ────→ RadioState.apply() ──→ @Published properties
  │     ◀── {"type":"set","field":"freq","value":14074000}
  │
  ├─ /WSspectrum (binary) → SpectrumProcessor.feed() → state.waterfallImage
  │     1-byte ver + 850B wf1 + 850B wf2 (1701B/frame)
  │
  ├─ /WSaudioRX (binary)  → tag check → OpusDecoder/PCM → AudioPlaybackManager
  │     1-byte codec tag (0x00=PCM, 0x01=Opus) + payload
  │
  └─ /WSaudioTX (binary)  ← AudioCaptureManager → OpusEncoder/PCM → WS
        1-byte codec tag + payload
```

### State Management

```
RadioState (@ObservableObject, @MainActor)
  ~50 @Published properties
  ├─ VFO: vfo_a_freq, vfo_b_freq, active_vfo, mode, tx_status
  ├─ Meters: s_meter, power_meter, alc_meter, swr_meter, id_meter, vd_meter
  ├─ Settings: af_gain, rf_gain, rf_power, squelch, mic_gain, preamp, attenuator
  ├─ DSP: noise_blanker, noise_reduction, auto_notch, compressor, agc, contour_level
  ├─ Scope: scope_span, scope_mode, scope_start_freq
  ├─ Tuner: tuner_status (0=OFF, 1=ON, 2=Tuning)
  ├─ PTT/Power: tx_status, power_on, split, vox
  ├─ Connection: serial_connected, last_update
  ├─ Derived: s_meter_dbm, s_unit, power_watts, swr_ratio, band_name, mode_name
  ├─ Spectrum: waterfallImage (UIImage)
  └─ Audio: rmsLevel (Float)

RadioViewModel (@MainActor ObservableObject coordinator)
  ├─ state.objectWillChange → self.objectWillChange (nested relay)
  ├─ connection: ConnectionManager
  ├─ spectrumProcessor: SpectrumProcessor
  ├─ audioPlayback: AudioPlaybackManager
  ├─ audioCapture: AudioCaptureManager
  └─ Actions: powerOn(), sendControl(), recallMemory(), etc.
```

### Protocol (FT710-specific)

**Client → Server messages:**
- `{"type":"set","field":"<field>","value":<value>}` — set any radio field
- `{"type":"ping"}` — latency probe
- `{"type":"get","field":"fullState"}` — request full state
- `{"type":"memRecall","freq":<hz>,"mode":"<MODE>"}` — recall memory channel
- `{"type":"memSave","channels":[...]}` — save all memory channels
- `{"type":"memDelete","index":<n>}` — clear one channel
- `{"type":"memLoadAll"}` — reload all channels from server
- Legacy text: `"field:value"` (fallback, deprecated)

**Server → Client messages:**
- `{"type":"fullState","data":{...},"bands":[...],"modes":[...],"memChannels":[...]}` — initial sync
- `{"type":"stateUpdate","fields":{...},"dirty":[...]}` — incremental patch
- `{"type":"memChannels","channels":[...]}` — memory channel update
- `{"type":"pong"}` — latency response
- `{"type":"error","message":"..."}` — error feedback

**Settable fields (subset from server.py):**
`freq`, `vfo_a_freq`, `vfo_b_freq`, `mode`, `ptt`, `tune`, `filter`/`filter_width`, `af_gain`, `rf_gain`, `rf_power`, `preamp`, `att`/`attenuator`, `nb`/`noise_blanker`, `nr`/`noise_reduction`, `an`/`auto_notch`, `comp`/`compressor`, `tuner`, `vfo`, `split`, `power`, `squelch`, `mic_gain`, `scope_span`

## Project Structure

```
FT710Mobile/
├── project.yml                     # XcodeGen spec
├── CLAUDE.md                       # Developer reference
├── README.md
├── Resources/
│   └── Info.plist                  # Mic, background audio, ATS exceptions
└── Sources/
    ├── App/
    │   └── FT710MobileApp.swift    # @main, login/auto-login, Keychain
    ├── Model/
    │   ├── RadioState.swift        # ~50 @Published FT710 fields
    │   └── MemoryChannelsManager.swift
    ├── Networking/
    │   ├── WebSocketConnection.swift    # URLSessionWebSocketTask wrapper (adapted)
    │   └── ConnectionManager.swift      # 4-socket manager → /WSradio etc.
    ├── ViewModel/
    │   └── RadioViewModel.swift    # @MainActor coordinator
    ├── Audio/
    │   ├── AudioPlaybackManager.swift   # RX: PCM/Opus → AVAudioPlayerNode
    │   ├── AudioCaptureManager.swift    # TX: Mic → Int16 PCM → Opus encode
    │   ├── OpusDecoder.swift            # libopus wrapper
    │   └── OpusEncoder.swift            # libopus wrapper
    ├── Spectrum/
    │   └── SpectrumProcessor.swift       # 850B waterfall → UIImage
    └── UI/
        ├── ContentView.swift            # Main container, connection gate
        ├── HeaderView.swift             # Freq + VFO A/B + status
        ├── MainRXView.swift             # RX tab
        ├── WaterfallView.swift          # Spectrum display
        ├── FrequencyDisplay.swift       # Monospaced digits
        ├── SMeterView.swift             # S-meter bar
        ├── MeterBarView.swift           # PWR/SWR/ALC/Id/Vd meters
        ├── ModeSelectorView.swift       # Mode cycle
        ├── PTTButtonView.swift          # PTT + TUNE
        ├── DSPPanelView.swift           # NB/NR/AN/COMP/CONT/AGC
        ├── BandSelectorView.swift       # 12 ham bands
        ├── FilterSelectorView.swift     # Filter width
        ├── TunerView.swift              # Antenna tuner
        ├── MemoryChannelsView.swift     # 10-slot grid
        ├── SettingsView.swift           # Config, status, logout
        └── LoginView.swift              # Password login
```

### Build Configuration

- **Build system:** XcodeGen (`project.yml`)
- **Team:** `VQ89MM7935`
- **Bundle ID:** `com.hamradio.ft710mobile`
- **Deployment target:** iOS 17.0
- **Swift:** 5.9
- **Opus:** libopus via Swift Package Manager

## UI Screens

### Login Screen
- Server host (default: `radio.vlsc.net:8888`)
- Password field (secure text)
- Connect button
- Auto-login via Keychain-stored credential

### Main RX Screen (primary tab)
- **Header:** Connection status dots (CTRL/SPECT/RX/TX), S-meter peak reading, tuner state, power on/off indicator
- **VFO selector:** A/B segmented control
- **Frequency display:** Large monospaced digits (step up/down arrows), band picker (12 bands)
- **Waterfall:** 150pt spectrum waterfall with frequency scale overlay
- **Meter stack:** S-meter bar + PWR/SWR/ALC/Id/Vd mini-bars
- **Audio level:** RMS audio level bar
- **Gain sliders:** AF gain, RF gain, Squelch, Mic gain (all 0-255 range mapped to slider)
- **Mode + Filter row:** Mode cycle (< USB >), CW speed when applicable, filter width dropdown
- **DSP toggles:** NB, NR, AN, COMP — pill-style on/off toggles. PRE, ATT level pickers. AGC mode picker.
- **Memory channels:** 10-slot scrollable grid. Tap to recall (sends `memRecall` with freq+mode). Long-press to save current freq/mode. Swipe to clear.
- **Bottom bar:** TUNE button (left) + large TX/PTT button (right)

### Settings Screen (secondary tab)
- Server host config + Reconnect button
- Connection status indicators (4 dots)
- RF power slider
- Scope span picker
- Memory channels: quick save current, clear all
- About section + Logout

## Audio Pipeline

### RX
1. `/WSaudioRX` WebSocket delivers binary frames
2. Read 1-byte codec tag
3. Tag `0x00` (PCM): Int16 LE → Float32 → AVAudioPCMBuffer → scheduleBuffer()
4. Tag `0x01` (Opus): decode via OpusDecoder → Int16 PCM → Float32 → scheduleBuffer()
5. Source sample rate: 48000 Hz (matches server `RX_OUT_RATE`)
6. RMS level computed for audio meter bar

### TX
1. Mic tap at native rate → downsample to 16000 Hz
2. Accumulate 320-sample frames (20ms at 16kHz)
3. Encode via OpusEncoder → tag with 0x01 → send binary
4. Or send raw Int16 PCM tagged 0x00
5. TX owner guard: stop sending on WebSocket disconnect
6. PTT safety timeout: auto-release if no heartbeat

## Spectrum Pipeline

1. `/WSspectrum` WebSocket delivers binary frames (~30fps)
2. Parse: 1-byte version (0x01) + 850 bytes wf1 + 850 bytes wf2
3. Background queue processing:
   - Accumulate N rows → build waterfall bitmap
   - Color map: match web frontend palette (dark blue → cyan → yellow → red)
   - Scroll pixel buffer + build CGImage → UIImage
   - Dispatch to main: state.waterfallImage = img
4. WaterfallView displays pre-rendered UIImage (no processing on main thread)
5. Dynamic frequency scale overlay based on scope_start_freq + scope_span

## Key Differences from SunsdrMobile Reference

| Area | SunsdrMobile | FT710Mobile |
|------|-------------|-------------|
| WS paths | `/WSCTRX`, `/WSaudioRX`, etc. | `/WSradio`, `/WSaudioRX`, etc. |
| Auth cookie | `sunmrrc_auth` | `ft710_auth` |
| Protocol | `"cmd:val"` text | JSON `{"type":"set","field":...}` |
| VFO | Single frequency | VFO A + VFO B + active selector |
| Modes | USB/LSB/CW/AM/FM/WFM | USB/LSB/CW-U/CW-L/AM/FM/RTTY-L/RTTY-U/DATA-L/DATA-U/PSK |
| DSP | WDSP (NR2, ANF, NF, notches) | FT-710 native (NB, NR, AN, COMP, CONT, AGC) |
| Meters | S-meter only | S + PWR + SWR + ALC + Id + Vd |
| Spectrum | 512-bin FFT | 850-byte waterfall (scope data) |
| Bands | 12 presets | 12 ham bands (160m–4m) |
| Tuner | N/A | Antenna tuner with TUNE button |
| Memories | 3×3 grid UserDefaults | 10-slot server-backed |
| Audio codec | PCM only | Opus + PCM |
| Filter | WDSP bandpass | CAT filter width index; UI shows curated voice/narrow subsets, current-Hz lookup uses full backend tables |
| Scope span | N/A | Selectable 1kHz–1MHz |

## Error Handling & Safety

- **PTT safety:** Auto-release TX on client disconnect (server handles this), client-side timeout watchdog
- **Auth failures:** WS close code 4001 → redirect to login
- **Connection loss:** Auto-reconnect with exponential backoff (1s, 2s, 4s, max 30s)
- **Audio underrun:** Silence fill in playback buffer
- **Spectrum drop:** Freeze last good frame, resume on next data
- **Serial disconnect:** Show "Radio not connected" state, retry

## Testing Strategy

- Protocol parsing unit tests (JSON state update messages)
- RadioState field update and dirty-tracking tests
- Spectrum frame parsing tests (1-byte header + 1700B payload)
- Opus encode/decode round-trip tests
- Manual: connect to real FT710, verify all controls, audio, spectrum
