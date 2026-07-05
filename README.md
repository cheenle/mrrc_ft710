# FT-710 Web Control

Web-based remote control server for the [Yaesu FT-710](https://www.yaesu.com/) HF/50MHz transceiver. Full browser-based control from any modern device — real-time waterfall spectrum, S-meter, frequency/mode/filter control, multi-meter telemetry (PWR/ALC/SWR/Id/Vd), PTT management, and memory channels. Mobile-first responsive UI optimized for iPhone/iOS Safari.

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

## Architecture

```
Browser (iPhone / Desktop / Tablet)
  ↕ HTTP + WebSocket (JSON control + binary spectrum)
FT-710 Server (Python FastAPI + Uvicorn)
  ├── ↕ Serial CAT (USB Enhanced COM Port, 38400 baud)
  ├── ↕ FT4222 SPI (scope_pipe subprocess → real spectrum data)
  └── ↕ S-meter fallback (synthetic spectrum when FT4222 unavailable)
Yaesu FT-710 Radio
```

**Dual-mode spectrum:**
- **FT4222 SPI mode**: Reads raw 4096-byte scope frames from the FTDI FT4222 chip via `libft4222.dylib`. Provides true 850-point FFT spectrum waterfall at ~21 fps. Requires compatible FTDI libraries and D2XX driver configuration.
- **S-meter fallback**: When the FT4222 is unavailable, generates a synthetic multi-peak spectrum from CAT S-meter readings — still provides real-time band activity visualization.

## FT4222 Scope Setup (Real Spectrum Data)

The FT-710 has a built-in FTDI FT4222 chip that outputs 850-point FFT spectrum data via SPI. To enable this:

### 1. FTDI Libraries

The project needs `libft4222.dylib` and `libftd2xx.dylib` in `FT710/lib/`.

**Important**: The `libft4222.dylib` version matters. The version bundled with [wfview](https://github.com/eliggett/wfview) (inside the macOS .app bundle at `Contents/Frameworks/`) is known to work. If scope reads stall with `TRANSFER_IN_PROGRESS`, try copying wfview's library:

```bash
cp /Applications/wfview.app/Contents/Frameworks/libft4222.dylib FT710/lib/
```

The `libftd2xx.dylib` from wfview is identical to the one included in this project.

### 2. D2XX Driver Configuration

On macOS, the FTDI VCP (Virtual COM Port) system extension claims the FT4222 device, preventing D2XX from accessing it. Create or update `/usr/local/lib/ftd2xx.cfg`:

```bash
sudo cp FT710/lib/ftd2xx.cfg /usr/local/lib/ftd2xx.cfg
```

This configuration enables `DetachKernelDriver=1` for the FT4222 chip (VID 0x0403, PID 0x601C), allowing D2XX to take control of the device.

### 3. SPI Clock Speed

The default SPI clock divider is `CLK_DIV_16` (value 5), giving 1.5 MHz SPI clock and ~21 fps scope data rate. Override via environment variable:

```bash
# Slower but more reliable (wfview default):
FT710_FT4222_CLK_DIV=7 python server.py   # CLK_DIV_64 → ~6 fps

# Faster (experimental):
FT710_FT4222_CLK_DIV=4 python server.py   # CLK_DIV_8 → ~30 fps
```

Valid range: 1-9. Lower = faster SPI clock.

### Verification

When scope data is flowing, the server log will show:

```
scope_pipe: first frame received — spectrum active (span=7, s_meter=157, wf1_max=237)
scope_pipe: diag:frames=30:fps=21.4:wf1_max=244:wf1_nz=850:span=7:s_meter=162
```

When FT4222 is unavailable, the log shows:

```
scope_pipe: spi_init_failed:all_attempts
scope_pipe exited (frames=0, connected=False)
Spectrum broadcast active: S-meter fallback, 1701 bytes/frame, 1 clients
```

## Project Structure

```
FT710/
├── server.py              # FastAPI app: lifespan, auth, WebSocket, REST, CLI
├── cat_controller.py      # Serial CAT protocol (pyserial + asyncio thread pool)
├── radio_state.py         # RadioState dataclass with dirty-field change tracking
├── poll_scheduler.py      # 5-tier background polling (100ms → 5s intervals)
├── scope_handler.py       # FT4222 SPI scope reader + S-meter fallback generator
├── scope_pipe.py          # Standalone FT4222 subprocess (avoids asyncio/ctypes issues)
├── scope_frame.py         # Shared frame parsing, pipe payload encode/decode, quality metrics
├── scope_libraries.py     # FTDI library discovery and SPI clock configuration
├── config.py              # Mode tables, bands, filter widths, S-meter calibration
├── requirements.txt       # fastapi, uvicorn, pyserial, websockets
├── start.sh               # Start server in background
├── stop.sh                # Stop background server
├── lib/
│   ├── libft4222.dylib    # FTDI FT4222 library (must match wfview version)
│   ├── libftd2xx.dylib    # FTDI D2XX library
│   └── ftd2xx.cfg         # D2XX config (copy to /usr/local/lib/)
├── static/
│   ├── index.html         # SPA shell (mobile-first responsive layout)
│   ├── ft710.css          # Dark amber theme, iPhone safe-area support
│   ├── ft710_main.js      # WebSocket client, state management, spectrum receiver
│   ├── ft710_ui.js        # All UI rendering: waterfall, S-meter, meters, controls
│   ├── manifest.json      # PWA manifest
│   ├── sw.js              # Service worker (offline cache)
│   └── modules/
│       ├── ptt_manager.js       # PTT safety watchdog + dead-man switch
│       └── settings_manager.js  # Cookie + localStorage persistence
├── tests/                 # Unit tests (10 tests covering scope, state, config)
├── mem_channels.json      # Persistent memory channels
├── venv/                  # Python virtual environment
└── logs/                  # Server log output
```

## Features

### Radio Control

| Feature | Implementation |
|---------|---------------|
| Frequency | 8-digit display (07.068.00), ±1k/±5k tuning, step cycling 10Hz–25kHz |
| Mode | Cycle button: LSB→USB→CW→AM→FM→RTTY→DATA; modal picker for all 15 modes |
| Band | Cycle button: 160m→80m→60m→40m→30m→20m→17m→15m→12m→10m→6m→4m |
| VFO | A/B toggle, A=B copy, Split toggle |
| Filter | Cycle through 23 voice or 21 narrow filter widths (mode-aware) |
| ATT / PRE | Cycle: OFF→6dB→12dB→18dB / OFF→AMP1→AMP2 |
| PTT | Touch-and-hold TX, release RX; triple TX0 verify; dead-man switch on WS disconnect |
| TUNE | Toggle button for antenna tuner activation |
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

### Spectrum Data Flow

```
FT-710 Radio → FT4222 SPI chip
  → scope_pipe.py (standalone subprocess, ctypes → libft4222)
    → stdout: [4-byte BE length][v2 payload: 1B version + 850B wf1 + 850B wf2 + metadata]
      → server.py _read_scope_pipe() (reads stdout, parses frames)
        → _broadcast_spectrum_loop() (30 fps to WebSocket clients)
          → /WSspectrum WebSocket (binary, 1701 bytes/frame)
            → ft710_main.js handleSpectrumBinary()
              → ft710_ui.js renderWaterfallRow()

Fallback path (no FT4222):
CAT SM0; poll (100ms)
  → radio_state.s_meter
    → scope_handler.update_from_radio_state()
      → Multi-peak Gaussian synthetic spectrum
        → /WSspectrum WebSocket (same binary format)
```

## Scope Pipe Protocol

The `scope_pipe.py` subprocess communicates with the server via:

**stdout** — Binary frame data:
```
[4-byte BE uint32 length][payload bytes...]
```
- Length 0: heartbeat (pipe alive, no data)
- Length > 0: v2 payload (version byte + wf1 + wf2 + metadata)

**stderr** — Machine-parseable status lines:
```
STATUS:spi_ready:attempt_1:clk_div_5
STATUS:diag:frames=30:fps=21.4:wf1_max=244:wf1_nz=850:span=7:s_meter=162
STATUS:heartbeat:frames=86:errors=0
STATUS:spi_stalled:reinit_after_50_in_progress
STATUS:sync_lost:bad_frame_1
STATUS:sync_recovered
STATUS:fatal:cannot_open_device
```

The server logs STATUS lines at INFO level for diagnostics, and WARNING level for errors (sync lost, stalls, reinitialization).

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
| `{"type":"set","field":"nb","value":false}` | Toggle NB |
| `{"type":"set","field":"att","value":2}` | Set attenuator |
| `{"type":"set","field":"preamp","value":1}` | Set preamp |
| `{"type":"set","field":"tuner","value":1}` | ATU on/off |
| `{"type":"set","field":"rf_power","value":100}` | RF power |
| `{"type":"set","field":"af_gain","value":128}` | AF gain |
| `{"type":"set","field":"mic_gain","value":50}` | Mic gain |
| `{"type":"set","field":"vfo","value":"A"}` | Switch VFO |
| `{"type":"set","field":"band","value":"20m"}` | Band select |
| `{"type":"set","field":"scope_span","value":6}` | Scope span index |
| `{"type":"set","field":"scope_speed","value":2}` | Scope speed |
| `{"type":"get","field":"fullState"}` | Request full state |
| `{"type":"memSave","channels":[...]}` | Save memories |

### `/WSspectrum?token=<auth_token>` (binary)

Each frame: **1-byte version (0x01)** + **850 bytes wf1 spectrum** + **850 bytes wf2 spectrum** = 1701 bytes total. Sent at up to 30 fps.

## REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Full radio state JSON (44 fields) |
| `/api/mem_channels` | GET | Memory channels |
| `/api/mem_channels` | POST | Save memory channels `{"channels":[...]}` |
| `/api/auth/login` | POST | Login `{"password":"..."}` → sets cookie |
| `/api/auth/logout` | POST | Logout → clears cookie |
| `/api/auth/check` | GET | Check auth status |

## CAT Command Reference

The server implements the full FT-710 CAT command set from wfview's `FT-710.rig`:

| CAT Command | Function |
|-------------|----------|
| `FA` / `FB` | VFO-A / VFO-B frequency (9-digit Hz) |
| `MD0` | Operating mode (0x01–0x0F hex) |
| `TX` | PTT status (0=RX, 1=TX, 2=TUNE) |
| `SM0` | S-meter (0–255) |
| `SH0` | Filter width index |
| `AG` | AF gain (0–255) |
| `PC` | RF power (5–100) |
| `PA0` | Preamp (0=OFF, 1=AMP1, 2=AMP2) |
| `RA0` | Attenuator (0–3) |
| `NB0` / `NR0` / `BC` | Noise blanker / NR / Auto notch |
| `PR` / `PL` | Compressor on/off / level |
| `AC` | ATU status (0=OFF, 1=ON, 2=TUNE) |
| `PS` | Power on/off |
| `BS` | Band stacking register |
| `VS0` / `VS1` | VFO A/B select |
| `ST` | Split on/off |
| `SS00` / `SS05` / `SS06` | Scope speed / span / mode |
| `RM3–RM8` | Meter readings (Comp/ALC/PWR/SWR/Id/Vd) |
| `IF` | Information (25-byte combined response) |
| `ID` | Transceiver ID |

## Polling Strategy

5-tier background polling at 38400 baud (~296 bytes/sec total):

| Tier | Rate | Commands | Fields |
|------|------|----------|--------|
| 1 | 100ms | `FA;` `MD0;` `SM0;` | VFO freq, mode, S-meter |
| 2A | 500ms (TX only) | `RM4;` `RM5;` `RM6;` | ALC, Power, SWR |
| 2B | 500ms | `TX;` | PTT status (radio-originated) |
| 3 | 2s | `SH0;` `AG;` `PC;` `PA0;` `RA0;` `NB0;` `NR0;` `BC;` `AC;` | Filter, gains, preamp, att, NR, NB, AN, tuner |
| 4 | 5s | `RM7;` `RM8;` `PR;` | Drain current, voltage, compressor |

User commands jump the priority queue ahead of polls.

## Troubleshooting

### Serial port not found
```bash
ls /dev/cu.usbserial-*     # macOS
ls /dev/ttyUSB*             # Linux
```

### No frequency / S-meter updates
Check that the FT-710 Enhanced COM Port is selected (not Standard COM Port). CAT commands work only on the Enhanced port at 38400 baud.

### FT4222 scope not working (no real spectrum, only S-meter fallback)

1. **Check libraries**: Ensure `libft4222.dylib` is the version from wfview's app bundle:
   ```bash
   cp /Applications/wfview.app/Contents/Frameworks/libft4222.dylib FT710/lib/
   ```

2. **Configure D2XX driver**: Copy the FT4222 config to `/usr/local/lib/`:
   ```bash
   sudo cp FT710/lib/ftd2xx.cfg /usr/local/lib/ftd2xx.cfg
   ```
   This enables `DetachKernelDriver=1` for the FT4222 chip, preventing the macOS VCP driver from claiming the device.

3. **Close other applications**: Only one process can access the FT4222 at a time. Close wfview, ExpertSDR, or any other app using the FT-710 before starting the server.

4. **Check device presence**: The FT4222 should appear in IORegistry:
   ```bash
   ioreg -p IOUSB -w0 -l | grep FT4222
   ```

5. **Check server logs**: Real scope data shows:
   ```
   scope_pipe: first frame received — spectrum active (span=7, s_meter=157, wf1_max=237)
   ```
   Fallback mode shows:
   ```
   Spectrum broadcast active: S-meter fallback, 1701 bytes/frame, 1 clients
   ```

6. **Try different SPI clock**: If reads stall at `TRANSFER_IN_PROGRESS`:
   ```bash
   FT710_FT4222_CLK_DIV=7 python server.py   # Slower, more compatible
   ```

### iPhone no PTT / audio prompt
iOS Safari requires HTTPS for `getUserMedia`. Use a TLS reverse proxy (nginx) or connect via `https://` with a valid certificate.

## Requirements

- **Python 3.12** with: `fastapi`, `uvicorn[standard]`, `pyserial`, `websockets`
- **FT-710** connected via USB
  - Enhanced COM Port for CAT (38400 baud)
  - FT4222 chip (internal) for real scope data
- **For real FT4222 scope data**:
  - `libft4222.dylib` from wfview app bundle in `FT710/lib/`
  - `libftd2xx.dylib` in `FT710/lib/`
  - `ftd2xx.cfg` installed to `/usr/local/lib/` with `DetachKernelDriver=1`
- **Browser**: Safari 15+ (iOS), Chrome, Firefox (WebSocket + Canvas)

## Safety

- **PTT dead-man switch**: Touch-and-hold to TX, immediate release on touch-end
- **Triple TX0 verify**: 3× CAT `TX;` query after release at 200ms intervals
- **Server-side forced RX**: When last WebSocket client disconnects during TX, server sends `TX0;`
- **Browser unload beacon**: `beforeunload` + `pagehide` events force `TX0;` on tab close

## Tests

Run the test suite:

```bash
cd FT710
./venv/bin/python -m unittest discover -s tests -v
```

13 tests covering: scope frame parsing, pipe payload encoding, S-meter fallback, SPI clock configuration, scope CAT initialization, radio state serialization, and frame quality metrics.
