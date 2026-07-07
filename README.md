# FT-710 Web Control

Web-based remote control server for the [Yaesu FT-710](https://www.yaesu.com/) HF/50MHz transceiver. Full browser-based control from any modern device — bidirectional audio (RX/TX) with Opus compression, real-time waterfall spectrum, S-meter, frequency/mode/filter control, multi-meter telemetry (PWR/ALC/SWR/Id/Vd), PTT management, and memory channels. Mobile-first responsive UI optimized for iPhone/iOS Safari.

## Quick Start

```bash
cd FT710
pip install -r requirements.txt

# macOS (FT-710 Enhanced COM Port):
FT710_SERIAL_PORT=/dev/cu.usbserial-0121DB3A0 python server.py

# Linux:
FT710_SERIAL_PORT=/dev/ttyUSB0 python server.py
```

Open `http://localhost:8888` in a browser. Default password: `ft710`.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FT710_SERIAL_PORT` | `/dev/cu.SLAB_USBtoUART` | CAT serial port (Enhanced COM Port, 38400 baud) |
| `FT710_BAUD_RATE` | `38400` | CAT serial baud rate |
| `FT710_WEB_PORT` | `8888` | Web server port |
| `FT710_WEB_PASSWORD` | `ft710` | Login password |
| `FT710_WEB_HOST` | `0.0.0.0` | Bind address |
| `FT710_FTDI_LIB_DIR` | *(auto)* | Directory containing FTDI libraries |
| `FT710_FT4222_CLK_DIV` | `5` | SPI clock divider (1=fastest, 9=slowest). Default CLK_DIV_16 ≈ 21 fps |
| `FT710_SCOPE_PORT` | *(optional)* | Scope serial port (Standard COM Port, for SCU-LAN10 models) |
| `FT710_SCOPE_BAUD` | `115200` | Scope serial baud rate |
| `FT710_AUDIO_RX_DEVICE` | *(auto)* | Audio input device (index or name substring, e.g. `"FT-710"` or `"3"`) |
| `FT710_AUDIO_TX_DEVICE` | *(auto)* | Audio output device (index or name substring) |

### CLI Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--port` | `8888` | Web server port |
| `--serial-port` | `/dev/cu.SLAB_USBtoUART` | CAT serial port |
| `--baud` | `38400` | CAT serial baud rate |
| `--password` | `ft710` | Login password |
| `--host` | `::` | Bind address (IPv6 dual-stack) |
| `--ssl-cert` | `certs/fullchain.pem` | SSL certificate file |
| `--ssl-key` | `certs/radio.vlsc.net.key` | SSL private key file |
| `--no-ssl` | *(flag)* | Disable SSL (plain HTTP) |

## Architecture

```
Browser (iPhone / Desktop / Tablet)
  ↕ HTTP + WebSocket (4 channels: control, audio RX, audio TX, spectrum)
FT-710 Server (Python FastAPI + Uvicorn)
  ├── ↕ Serial CAT (USB Enhanced COM Port, 38400 baud)
  ├── ↕ FT4222 SPI (scope_pipe subprocess → real spectrum data)
  ├── ↕ S-meter fallback (synthetic spectrum when FT4222 unavailable)
  └── ↕ USB Audio (PyAudio capture/playback → Opus codec → browser)
Yaesu FT-710 Radio
```

### WebSocket Endpoints

| Endpoint | Protocol | Description |
|----------|----------|-------------|
| `/WSradio` | JSON text | Control commands, state updates, memory management |
| `/WSaudioRX` | Binary tagged | RX audio: 1-byte codec tag (0x00=PCM, 0x01=Opus 48kHz) + payload |
| `/WSaudioTX` | Binary tagged + text | TX mic uplink: tagged audio frames + text control (`s:` stop, `m:` settings) |
| `/WSspectrum` | Binary | Spectrum frames: v1=851B (1B ver + 850B wf1), v2=1701B (+850B wf2), ~30fps |

### Dual-Mode Spectrum

- **FT4222 SPI mode**: Reads raw 4096-byte scope frames from the FTDI FT4222 chip via `libft4222.dylib`. Provides true 850-point FFT spectrum waterfall at ~21 fps.
- **S-meter fallback**: When the FT4222 is unavailable, generates a synthetic multi-peak spectrum from CAT S-meter readings — still provides real-time band activity visualization.

### Audio Pipeline

**RX Audio:**
```
FT-710 USB Audio → PyAudio capture (44.1kHz Int16) → Resample 44.1k→48k
  → Opus encode (64kbps) → /WSaudioRX tagged frames (parallel send via asyncio.gather)
    → Browser WASM OpusDecoder → AudioWorklet 'rx-player'
      (jitter buffer: 220ms prebuffer, 90ms recovery) → Speakers
```

**TX Audio:**
```
Microphone → getUserMedia (48kHz) → ScriptProcessor (512buf, ~10.7ms)
  → Float32→Int16 → Opus Worker encode (48kHz, 960-sample frames, 64kbps CBR)
    → /WSaudioTX tagged frames (1B tag 0x01 + Opus packet)
      → Server TxOpusDecoder (48kHz) → Int16 PCM (960 samples/20ms)
        → Resample 48k→44.1k (linear interp, 160:147 exact ratio, phase-continuous)
          → _tx_queue (jitter buffer: 60ms pre-buffer, 400ms hard cap)
            → PyAudio playback (44.1kHz, mono) → FT-710 USB Audio Input
```

TX chain resamples from Opus 48kHz to the FT-710's native 44.1kHz USB audio rate using linear interpolation at an exact 160:147 ratio — frame boundaries stay phase-continuous so no periodic clicks.

**TX audio stability (v1.2):**
- **Jitter buffer**: Pre-buffers 60ms before first DAC write to absorb WebSocket jitter; hard cap at 400ms with oldest-first drop bounds latency under Wi-Fi stalls.
- **Graceful PTT release**: On PTT off, queued audio is written to the device buffer and `Pa_StopStream` blocks until the DAC finishes playing — word-endings survive before RF drops (TX_DRAIN=50ms).
- **`start_tx` is awaited** (not background): avoids a race where the drain loop queues mic frames before the PortAudio stream opens and `start_tx` clears the queue, which would cause SSB zero-power (no modulation).
- **Dual write-lock**: `_tx_write_lock` serializes the periodic drain-loop and the graceful stop so only one thread writes the PortAudio stream at a time (PortAudio blocking I/O is not thread-safe per stream).
- **Single-owner TX**: Only the first connected `/WSaudioTX` client's audio reaches the radio; subsequent clients' frames are ignored until the owner disconnects.

Opus falls back to Int16 PCM when libopus is unavailable (server or browser).

## Project Structure

```
FT710/
├── server.py              # FastAPI app: lifespan, auth, 4 WebSockets, REST, CLI
├── cat_controller.py      # Serial CAT protocol (pyserial + asyncio thread pool)
├── radio_state.py         # RadioState dataclass with dirty-field change tracking
├── poll_scheduler.py      # 7-tier background polling (100ms → 5s, bounded lock)
├── audio_handler.py       # PyAudio capture/playback + Opus encode + device detection
├── opus_rx.py             # libopus ctypes wrapper (RxOpusEncoder + TxOpusDecoder)
├── scope_handler.py       # FT4222 SPI scope reader + S-meter fallback generator
├── scope_pipe.py          # Standalone FT4222 subprocess (avoids asyncio/ctypes issues)
├── scope_frame.py         # Shared frame parsing, pipe payload encode/decode
├── scope_libraries.py     # FTDI library discovery and SPI clock configuration
├── config.py              # Mode tables, bands, filter widths, S-meter calibration
├── requirements.txt       # fastapi, uvicorn, pyserial, websockets, pyaudio, numpy
├── start.sh               # Start server in background
├── stop.sh                # Stop background server
├── lib/
│   ├── libft4222.dylib    # FTDI FT4222 library (must match wfview version)
│   ├── libftd2xx.dylib    # FTDI D2XX library
│   └── ftd2xx.cfg         # D2XX config (copy to /usr/local/lib/)
├── static/
│   ├── index.html         # SPA shell (mobile-first responsive layout)
│   ├── ft710.css          # Dark amber theme, iPhone safe-area support
│   ├── ft710_main.js      # WebSocket client (4 channels), state, audio, spectrum
│   ├── ft710_ui.js        # All UI rendering: waterfall, S-meter, meters, controls
│   ├── rx_worklet_processor.js  # AudioWorklet RX playback with jitter buffer
│   ├── tx_capture_worklet.js    # AudioWorklet mic capture
│   ├── tx_opus_worker.js        # Web Worker Opus encoder for TX
│   ├── manifest.json      # PWA manifest
│   ├── sw.js              # Service worker (offline cache)
│   └── modules/
│       ├── ptt_manager.js       # PTT safety watchdog + dead-man switch
│       ├── settings_manager.js  # Cookie + localStorage persistence
│       ├── opus_codec.js        # Browser WASM Opus encoder/decoder
│       └── opus_wasm.js         # Emscripten-compiled libopus WASM binary
├── SDD/                   # Software Design Description (15-chapter TeamSD docs)
├── tests/                 # Unit tests
├── mem_channels.json      # Persistent memory channels
└── logs/                  # Server log output
```

## Features

### Radio Control

| Feature | Implementation |
|---------|---------------|
| Frequency | 8-digit display, ±1k/±5k tuning, step cycling 10Hz–25kHz |
| Mode | Cycle button: LSB→USB→CW→AM→FM→RTTY→DATA; modal picker for all 15 modes |
| Band | Cycle button: 160m→80m→60m→40m→30m→20m→17m→15m→12m→10m→6m→4m |
| VFO | A/B toggle, A=B copy, Split toggle |
| Filter | Cycle through 23 voice or 21 narrow filter widths (mode-aware) |
| ATT / PRE | Cycle: OFF→6dB→12dB→18dB / OFF→AMP1→AMP2 |
| PTT | Touch-and-hold TX, release RX; triple TX0 verify; dead-man switch; graceful audio drain before RF drop |
| TUNE | Toggle button for antenna tuner activation |
| Wake Lock | ☀ toggle: screen stays on during operation (Wake Lock API + video/audio fallback for iOS) |
| Fullscreen | ⛶ toggle: hides browser chrome for a dedicated control surface |
| NR / NB / AN | Independent toggle switches |
| Compressor / ATU | Toggle switches |
| RF Power | Slider 5–100W |
| AF Gain | Slider 0–255 |
| Mic Gain | Slider 0–100 |
| NR / NB Level | Individual sliders (1–15 / 0–10) |

### Visualizations

| Feature | Implementation |
|---------|---------------|
| Waterfall | 850-point real-time spectrum, 120-row history, black→blue→green→yellow→red colormap |
| Frequency scale | Auto-scaled labels below waterfall |
| S-Meter | Canvas horizontal bar, S1–S9+60 gradient, dBm digital readout |
| Multi-meter | 5 real-time horizontal bar meters: PWR (W), ALC, SWR, Id (A), Vd (V) |

### Audio

| Feature | Implementation |
|---------|---------------|
| RX Audio | PyAudio capture → Opus 64kbps → AudioWorklet playback |
| TX Audio | Browser mic (48kHz) → Opus 64kbps CBR → server TxOpusDecoder → resample 48→44.1k → PyAudio 44.1kHz → radio. Jitter buffer (60ms pre-buffer / 400ms cap) + graceful PTT drain (Pa_StopStream blocks until DAC finishes) |
| Codec | Tagged dual-codec: Opus (64kbps CBR TX, 64kbps RX) with Int16 PCM fallback |
| Bandwidth | Opus ~64kbps (12× smaller than 768kbps PCM) |

## Polling Strategy

5-tier background polling at 38400 baud (~296 bytes/sec total):

| Tier | Rate | Commands | Fields |
|------|------|----------|--------|
| 1 | 100ms | `FA;` `MD0;` `SM0;` | VFO freq, mode, S-meter |
| 2A | 500ms (TX only) | `RM4;` `RM5;` `RM6;` | ALC, Power, SWR (zeroed on RX transition) |
| 2B | 500ms | `TX;` | PTT status (also triggers TX-meter zero-reset on TX→RX transition) |
| 3 | 2s | `SH0;` `AG;` `PC;` `PA0;` `RA0;` `NB0;` `NR0;` `BC;` `AC;` | Filter, gains, preamp, att, NR, NB, AN, tuner |
| 4 | 5s | `RM7;` `RM8;` `PR;` | Drain current, voltage, compressor |

## WebSocket Protocol

### `/WSradio?token=<auth_token>` (JSON text)

**Server → Client:**

| Message | Description |
|---------|-------------|
| `{"type":"fullState","data":{...},"bands":[...],"modes":[...]}` | Initial full state |
| `{"type":"stateUpdate","fields":{...},"dirty":[...]}` | Partial changed-fields update |
| `{"type":"value","field":"freq","value":7050000}` | Single value reply |
| `{"type":"memChannels","channels":[...]}` | Memory channels sync |
| `{"type":"pong"}` | PING response |

**Client → Server:**

| Message | Example |
|---------|---------|
| `{"type":"set","field":"freq","value":14200000}` | Set VFO-A frequency |
| `{"type":"set","field":"mode","value":"USB"}` | Set mode |
| `{"type":"set","field":"ptt","value":true}` | PTT on/off |
| `{"type":"set","field":"filter","value":5}` | Set filter width index |
| `{"type":"set","field":"nr","value":true}` | Toggle NR |
| `{"type":"get","field":"fullState"}` | Request full state |
| `{"type":"memSave","channels":[...]}` | Save memories |

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Full radio state JSON (44+ fields) |
| `/api/mem_channels` | GET | Memory channels |
| `/api/mem_channels` | POST | Save memory channels `{"channels":[...]}` |
| `/api/auth/login` | POST | Login `{"password":"..."}` → sets cookie |
| `/api/auth/logout` | POST | Logout → clears cookie |
| `/api/auth/check` | GET | Check auth status |

## Safety

- **PTT dead-man switch**: Touch-and-hold to TX, immediate release on touch-end
- **Triple TX0 verify**: 3× CAT `TX;` query after release at 200ms intervals
- **Server-side forced RX**: When last WebSocket client disconnects during TX, server sends `TX0;`
- **Browser unload beacon**: `beforeunload` + `pagehide` events force `TX0;` on tab close
- **TX audio stop**: Audio stream stopped before RF on PTT release

## Tests

```bash
cd FT710
python -m unittest discover -s tests -v
```

## Requirements

- **Python 3.12** with: `fastapi`, `uvicorn[standard]`, `pyserial`, `websockets`, `pyaudio`, `numpy`
- **libopus** (optional, for compressed audio): `brew install opus` (macOS) or `apt install libopus0` (Linux)
- **FT-710** connected via USB
  - Enhanced COM Port for CAT (38400 baud)
  - FT4222 chip (internal) for real scope data
  - USB Audio interface for RX/TX audio
- **For real FT4222 scope data**:
  - `libft4222.dylib` from wfview app bundle in `FT710/lib/`
  - `libftd2xx.dylib` in `FT710/lib/`
  - `ftd2xx.cfg` installed to `/usr/local/lib/` with `DetachKernelDriver=1`
- **Browser**: Safari 15+ (iOS), Chrome, Firefox (WebSocket + Web Audio + Canvas)

## SDD Documentation

See [`SDD/`](SDD/) for the complete Software Design Description (15 chapters, IBM TeamSD v2.3.2 aligned):
- Executive summary, business direction, project definition
- System context, NFRs, use cases, subject area model
- Architecture decisions (10 ADs), architecture overview
- Service model, component model, operational model
- Feasibility assessment, version history, PTT safety architecture
