# CLAUDE.md — SunsdrMobile iOS App

## Overview

**SunsdrMobile** is a native iOS app (SwiftUI, iOS 17+) for the SunSDR2 DX amateur radio transceiver. It is a full replacement for the `sunmrrc` web frontend, communicating with the Python FastAPI backend at `https://radio.vlsc.net:8889` via 4 WebSocket connections. The app supports real-time audio playback, spectrum waterfall, DSP controls, band/mode/filter management, frequency presets, and PTT transmission.

## Build & Run

```bash
# Generate Xcode project
xcodegen generate

# Open in Xcode
open SunsdrMobile.xcodeproj

# Command-line build (unsigned)
xcodebuild -project SunsdrMobile.xcodeproj -scheme SunsdrMobile \
  -sdk iphoneos -destination 'generic/platform=iOS' \
  CODE_SIGN_IDENTITY="" CODE_SIGNING_REQUIRED=NO build
```

- Requires Xcode 15+ with iOS 17.0 SDK
- Physical device required for audio (simulator lacks full AVAudioEngine mic support)
- Signing: `DEVELOPMENT_TEAM: VQ89MM7935`, automatic code signing

## Project Layout

```
SunsdrMobile/
├── project.yml                     # XcodeGen project spec
├── CLAUDE.md
├── Resources/
│   └── Info.plist                  # Mic permission, background audio, ATS
└── Sources/
    ├── App/
    │   └── SunsdrMobileApp.swift   # @main entry, login/auto-login, Keychain
    ├── Model/
    │   ├── RadioState.swift        # @Published central state (~30 properties)
    │   └── FavoritesManager.swift  # UserDefaults-persisted channel presets
    ├── Networking/
    │   ├── WebSocketConnection.swift  # URLSessionWebSocketTask wrapper
    │   └── ConnectionManager.swift    # Manages 4 WS sockets + auth
    ├── ViewModel/
    │   └── RadioViewModel.swift    # Central @ObservableObject coordinator
    ├── Audio/
    │   ├── AudioPlaybackManager.swift  # RX: Int16 PCM → AVAudioPlayerNode
    │   ├── AudioCaptureManager.swift   # TX: Mic → downsample → Int16 PCM
    │   └── SpectrumProcessor.swift     # Background waterfall rendering
    └── UI/
        ├── ContentView.swift       # Main container, power-on gate
        ├── HeaderView.swift        # Frequency + band + step + status bar
        ├── MainRXView.swift        # RX tab: waterfall, gains, PTT, favs grid
        ├── WaterfallView.swift     # Displays pre-rendered waterfall UIImage
        ├── FrequencyDisplay.swift  # Large 56pt monospaced frequency digits
        ├── SMeterView.swift        # S-meter bar (S0–S9+)
        ├── ModeSelectorView.swift  # Rotary mode selector (< USB >)
        ├── PTTButtonView.swift     # 96pt red TX button (long-press)
        ├── DSPPanelView.swift      # WDSP, NR2, AGC, notches
        ├── SettingsView.swift      # Favorites, server, audio, IQ rate
        └── LoginView.swift         # Password-only login form
```

## Architecture

### Data Flow

```
Server (radio.vlsc.net:8889)
  │
  ├─ /WSCTRX (text) ────→ RadioState.apply() ──→ @Published properties
  ├─ /WSaudioRX (binary) → AudioPlaybackManager.enqueue() → AVAudioPlayerNode
  ├─ /WSaudioTX (binary) ← AudioCaptureManager.onFrame ← Mic
  └─ /WSspectrum (binary) → SpectrumProcessor.feed() → state.waterfallImage
```

### Central State: `RadioState`

`RadioState` is an `@ObservableObject` marked `@MainActor` with ~30 `@Published` properties:
- **Frequency**: `frequency` (Hz), `iqSampleRateHz`, `mode`
- **Connection**: `ctrlConnected`, `audioRXConnected`, `audioTXConnected`, `spectrumConnected`
- **Audio**: `afGain`, `rfGain`, `squelch`, `signalLevel`, `latency`
- **DSP**: `wdspEnabled`, `nr2Enabled/Level`, `nbEnabled`, `anfEnabled`, `nfEnabled`, `agcMode`, `filterLow/High`, `notches`
- **PTT**: `ptt`, `powerOn`
- **Spectrum**: `spectrumData` (raw 512B), `waterfallImage` (pre-rendered), `iqSampleRateHz`

Server messages are parsed in `apply(serverMessage:)` via `cmd:val` protocol. Properties are defined in `RadioState.swift` along with:
- `bands`: 12 band presets (160m–2m)
- `sampleRateMapping`: IQ rate keys → Hz (`39k→39062, 78k→78125, 156k→156250, 312k→312500`)
- `sampleRateOptions`: Menu labels for Settings UI

### ViewModel: `RadioViewModel`

`RadioViewModel` is the `@MainActor` `ObservableObject` coordinator:
- **Nested ObservableObject forwarding**: `state.objectWillChange.sink { self.objectWillChange.send() }` so SwiftUI re-renders when state changes
- **Auth**: `powerOnAsync()` → POST `/api/auth/login` → extract `sunmrrc_auth` cookie → `connection.updateCredentials(token)` → `bindSockets()` → `connectAll()`
- **Control commands**: `sendControl("cmd:val")` pattern for freq, mode, PTT, DSP, etc.
- **Spectrum**: feeds data to `SpectrumProcessor` which processes on background queue and publishes final `UIImage` to `state.waterfallImage`

### Spectrum Architecture (CPU-optimized)

Spectrum processing is completely off the main thread:

```
WebSocket callback (background serial queue)
  → SpectrumProcessor.feed()  [frame skip: every other frame dropped]
    → dispatch to background queue (.userInteractive)
      → accumulate 5 frames
      → sort + LUT + contrast stretch
      → scroll pixel buffer + build CGImage → UIImage
      → DispatchQueue.main: state.waterfallImage = img
        → WaterfallView displays the image (no processing)
```

Key parameters (match web frontend `controls.js`):
- `wfDecimate=5`, `wfPctl=0.30`, `wfHeadroom=2`, `wfGain=8.0`, `wfBias=52`
- 512-bin spectrum rows, 100-row waterfall history
- Throttled to ≤10 fps

### Audio Pipeline

**RX** (`AudioPlaybackManager`):
- Server sends audio frames with 1-byte codec tag (`0x00`=PCM Int16, `0x01`=Opus)
- Opus frames are skipped (server sends Opus by default; set `setOpus:false`)
- PCM: Int16 LE → Float32 conversion → AVAudioPCMBuffer → `playerNode.scheduleBuffer()`
- Source sample rate: 48000 Hz (matches server `RX_OUT_RATE`)
- RMS level updated for audio meter bar

**TX** (`AudioCaptureManager`):
- Mic tap at native rate → downsample (48k→16k) → 320-sample frame accumulation
- Int16 PCM → `onFrame` callback → `/WSaudioTX` WebSocket

### UI Layout

**Header** (`HeaderView`):
```
Row 1: ☰  ●CTRL ●RX ●TX ●FFT  USB  S5  23ms  ⏻
Row 2: [◀]  14.074.000  [▶]              (step arrows + big frequency)
Row 3: [20m▼]                    [1K▼]    (band picker + step picker)
```

**Main RX** (`MainRXView`):
```
S-meter
Waterfall (120pt) + dynamic freq scale
🔊 audio level bar
AF / RF / SQL gain sliders
──────────────────
[< USB >]  [< SSB >]            (mode + filter, one row)
┌──────┐ ┌──────┐ ┌──────┐
│ CH1  │ │ CH2  │ │  --- │       (3×3 favorites grid)
│14.074│ │ 7.074│ │---.--│       (always 9 cells, empty=placeholder)
└──────┘ └──────┘ └──────┘
──────────────────
        [TX]                     (PTT at bottom, 96pt)
```

**Settings** (`SettingsView`):
- Quick-save current freq/mode
- Favorites list with swipe-delete
- Server host config + reconnect
- Connection status indicators
- AF gain slider + IQ sample rate picker (39k/78k/156k/312k)
- Clear all favorites, About section

### IQ Sample Rate

Configurable via Settings → 音频 → IQ 采样率 picker. Sends `setSampleRate:39k|78k|156k|312k` to server, which triggers a full hardware re-boot sequence with the new rate. The waterfall frequency scale dynamically adjusts to the current IQ bandwidth.

## Key Conventions

- **No audio processing on main thread** — spectrum is entirely on background queue; audio conversion is on WebSocket callback queue
- **@MainActor for state** — `RadioState` and `RadioViewModel` are main-actor-isolated; UI observes via `@EnvironmentObject` / `@Published`
- **Nested ObservableObject relay** — `state.objectWillChange → viewModel.objectWillChange` so ContentView sees deep changes
- **Privacy** — microphone permission in Info.plist; ATS allows arbitrary loads for self-signed certs
- **Auth** — password only (no username); Keychain-stored; token passed as `?token=` WebSocket query param
- **Step sizes** — 1K (default), 5K, 10K, 50K, 100K
- **Bands** — 12 presets from 160m to 2m, displayed as Picker menu
- **Favorites** — 3×3 grid always visible; empty cells show `---` placeholder; persisted via UserDefaults JSON
