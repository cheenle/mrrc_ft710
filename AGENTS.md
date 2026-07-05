# Repository Guidelines

## Project Structure & Module Organization

This repository contains a Python FastAPI server for Yaesu FT-710 web control plus a static browser UI. Core backend modules live at the repository root:

| Module | Responsibility |
|--------|----------------|
| `server.py` | FastAPI app, auth, 4 WebSocket endpoints, REST APIs, lifespan management |
| `cat_controller.py` | Serial CAT protocol (pyserial + asyncio.to_thread), 40+ command helpers |
| `radio_state.py` | `RadioState` dataclass with dirty-field change tracking and derived properties |
| `poll_scheduler.py` | 5-tier adaptive background polling (100ms→5s) with skip-on-command |
| `audio_handler.py` | PyAudio sound card capture/playback, Opus encode, FT-710 device auto-detection |
| `opus_rx.py` | libopus ctypes wrapper: `RxOpusEncoder` (48kHz), `TxOpusDecoder` (16kHz) |
| `scope_handler.py` | Spectrum data container: FT4222 real FFT + S-meter Gaussian fallback |
| `scope_pipe.py` | Standalone subprocess for FT4222 SPI I/O (avoids asyncio/ctypes conflicts) |
| `scope_frame.py` | Shared frame parsing, pipe payload encode/decode, quality metrics |
| `scope_libraries.py` | FTDI library discovery and SPI clock configuration |
| `config.py` | Mode tables, bands, filter widths, S-meter calibration, all constants |

Frontend assets in `static/`:
- `index.html` — SPA shell (mobile-first responsive layout)
- `ft710.css` — Dark amber theme, iPhone safe-area support
- `ft710_main.js` — WebSocket client (4 channels), state management, audio RX/TX, spectrum
- `ft710_ui.js` — All UI rendering: waterfall, S-meter, meters, controls, PTT
- `rx_worklet_processor.js` — AudioWorklet: time-based jitter buffer RX playback
- `tx_capture_worklet.js` — AudioWorklet: mic capture with 48k→16k downsample
- `tx_opus_worker.js` — Web Worker: Opus encode from mic samples
- `modules/opus_codec.js` + `opus_wasm.js` — Browser-side WASM Opus codec
- `modules/ptt_manager.js` — PTT state machine + safety watchdog
- `modules/settings_manager.js` — Cookie + localStorage persistence

SDD (Software Design Description) in `SDD/` — 15-chapter IBM TeamSD documentation.

## Build, Test, and Development Commands

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the server:
```bash
FT710_SERIAL_PORT=/dev/cu.usbserial-0121DB3A0 python server.py
```

Run tests:
```bash
python -m unittest discover -s tests -v
```

Environment variables: `FT710_SERIAL_PORT`, `FT710_BAUD_RATE`, `FT710_WEB_PORT`, `FT710_WEB_PASSWORD`, `FT710_WEB_HOST`, `FT710_FTDI_LIB_DIR`, `FT710_FT4222_CLK_DIV`, `FT710_SCOPE_PORT`, `FT710_SCOPE_BAUD`.

## Coding Style & Naming Conventions

Python: 4-space indentation, type hints for shared state, `UPPER_CASE` for module constants, `PascalCase` for classes, `snake_case` for functions/variables. JavaScript: `camelCase` names; UI rendering in `ft710_ui.js` or `static/modules/`; avoid mixing logic into `index.html`.

## Testing Guidelines

No configured pytest suite yet. At minimum: `python -m py_compile *.py`. Hardware-dependent changes should document: connected FT-710, serial port, FT4222 availability, audio device. Name tests `test_*.py`. Keep hardware-independent logic testable without a radio.

## Commit & Pull Request Guidelines

Short imperative summaries. Pull requests should describe user-visible behavior, list verification steps, call out hardware requirements, and include screenshots/recordings for UI changes.

## Security & Configuration Tips

Never commit passwords, serial-device paths, or local driver assumptions. Use environment variables for deployment-specific values. All WebSocket endpoints require auth token (`?token=` query param). Auth tokens cleared on server restart.
