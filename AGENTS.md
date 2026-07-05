# Repository Guidelines

## Project Structure & Module Organization

This repository contains a Python FastAPI server for Yaesu FT-710 web control plus a static browser UI. Core backend modules live at the repository root: `server.py` owns the FastAPI app, auth, REST, and WebSocket endpoints; `cat_controller.py` handles CAT serial protocol; `radio_state.py` stores shared radio state; `poll_scheduler.py` manages polling cadence; `scope_handler.py` handles spectrum data; and `config.py` centralizes constants and mode/band tables. Frontend assets are in `static/`, with `index.html`, `ft710.css`, `ft710_main.js`, `ft710_ui.js`, and focused modules under `static/modules/`. Persistent memory channels are stored in `mem_channels.json`.

## Build, Test, and Development Commands

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the local server:

```bash
FT710_SERIAL_PORT=/dev/cu.usbserial-0121DB3A0 python server.py
```

Use `FT710_WEB_PORT=8888`, `FT710_WEB_PASSWORD=...`, and related environment variables from `README.md` to adjust runtime configuration. The app is served at `http://localhost:8888`. For hardware scope checks, run `_test_ft4222.py` only on a machine with the required FTDI libraries and device access.

## Coding Style & Naming Conventions

Use Python 3.12 syntax and keep backend code consistent with the existing style: 4-space indentation, type hints for shared state and helpers, module-level constants in `UPPER_CASE`, classes in `PascalCase`, and functions or variables in `snake_case`. Frontend files use plain JavaScript modules; prefer `camelCase` names and keep UI rendering logic in `ft710_ui.js` or `static/modules/` rather than mixing it into `index.html`.

## Testing Guidelines

There is no configured pytest suite yet. For backend changes, at minimum run `python -m py_compile *.py` and manually exercise affected REST/WebSocket behavior through the browser. Hardware-specific changes should document the connected FT-710, serial port, and whether real FT4222 scope data or S-meter fallback was used. Name future tests `test_*.py` and keep hardware-independent logic testable without a connected radio.

## Commit & Pull Request Guidelines

Recent commits use short imperative summaries, for example `Update copyright and repository links to GitHub`. Keep commit subjects concise and focused on one change. Pull requests should describe user-visible behavior, list manual or automated verification steps, call out hardware requirements, and include screenshots or short recordings for UI changes.

## Security & Configuration Tips

Do not commit private passwords, serial-device assumptions, or local driver paths. Prefer environment variables for deployment-specific values, especially `FT710_WEB_PASSWORD`, `FT710_SERIAL_PORT`, and bind host settings.
