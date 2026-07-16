# FT-710 Web Control — Quick Start Guide

## 🚀 Immediate Setup (5 minutes)

### Prerequisites

- **Python 3.10+** installed (`python3 --version`)
- **FT-710** connected via USB to your computer
- **Browser**: Safari 15+, Chrome, or Firefox

### Windows Installer Path

On Windows 11/12, prefer the desktop installer. It embeds Python and starts the
server from a launcher window.

```powershell
# Build on Windows:
packaging\windows\build.ps1

# Then install:
dist\windows\MRRC-FT710-Setup.exe
```

Configuration is stored at:

```text
%LOCALAPPDATA%\MRRC-FT710\ft710.env
```

See [docs/WINDOWS_INSTALLER_GUIDE.md](docs/WINDOWS_INSTALLER_GUIDE.md).

### 1. Install Dependencies

```bash
cd /Users/cheenle/HAM/mrrc_ft710
pip3 install -r requirements.txt
```

### 2. Configure Security (REQUIRED)

```bash
# Set a strong password (16+ characters recommended)
export FT710_WEB_PASSWORD="YourStrongPassword123!"

# Optional: Change port (default: 8888)
export FT710_WEB_PORT="8888"

# Optional: Bind to localhost only (more secure)
export FT710_WEB_HOST="127.0.0.1"
```

### 3. Start the Server

```bash
# macOS (FT-710 Enhanced COM Port):
FT710_SERIAL_PORT=/dev/cu.usbserial-0121DB3A0 python3 server.py

# Linux:
FT710_SERIAL_PORT=/dev/ttyUSB0 python3 server.py

# Or use the convenience script:
./start.sh
```

### 4. Open in Browser

Navigate to: **http://localhost:8888**

Enter your password when prompted.

---

## 🔧 Optional: FT4222 Spectrum (Real FFT Data)

For true 850-point FFT spectrum waterfall:

1. macOS: copy `libft4222.dylib` and `libftd2xx.dylib` to `mrrc_ft710/lib/`, then install `ftd2xx.cfg` to `/usr/local/lib/` with `DetachKernelDriver=1`.
2. Linux: copy compatible `libft4222.so` and `libftd2xx.so` to `mrrc_ft710/lib/` or set `FT710_FTDI_LIB_DIR`.
3. Windows installer: place `FT4222.dll` and `ftd2xx.dll` in `vendor\ftdi\windows\bin\x64` before running `packaging\windows\build.ps1`.

Without FT4222, the app falls back to S-meter-based synthetic spectrum.

---

## 🎤 Audio Setup

The server uses PyAudio (PortAudio) for USB audio capture/playback:

- **RX**: Captures from FT-710 USB Audio interface (44.1kHz)
- **TX**: Sends to FT-710 USB Audio input (44.1kHz)

If you have multiple audio devices, specify them:

```bash
export FT710_AUDIO_RX_DEVICE="FT-710"   # Match by name
export FT710_AUDIO_TX_DEVICE="3"         # Match by index
```

---

## 🏥 Health Check

```bash
curl http://localhost:8888/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "radio_connected": true,
  "uptime_seconds": 120,
  "clients": 1
}
```

---

## 🛑 Stop the Server

```bash
./stop.sh
# Or press Ctrl+C in the terminal
```

---

## 📋 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Serial port not found" | Check `FT710_SERIAL_PORT` matches your device |
| "Audio device not found" | Check `FT710_AUDIO_RX_DEVICE` / `FT710_AUDIO_TX_DEVICE` |
| "Permission denied" on serial | Add user to dialout group (Linux) or check USB permissions (macOS) |
| Login rate limited | Wait 5 minutes or check your IP |
| No audio | Ensure libopus is installed: `brew install opus` (macOS) |
| Spectrum shows flat line | FT4222 not detected — check macOS/Linux `lib/` libraries or Windows `vendor\ftdi\windows\bin\x64` DLLs |

---

## 📖 More Documentation

- [SECURITY_GUIDE.md](SECURITY_GUIDE.md) — Security configuration details
- [DEPENDENCIES.md](DEPENDENCIES.md) — Cross-platform dependency guide
- [docs/WINDOWS_INSTALLER_GUIDE.md](docs/WINDOWS_INSTALLER_GUIDE.md) — Windows installer and FT4222 packaging
- [README.md](README.md) — Full feature documentation
- [SDD/](SDD/) — Software Design Description
