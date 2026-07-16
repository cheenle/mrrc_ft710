from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


APP_NAME = "MRRC FT-710"
DEFAULT_PORT = "8888"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def user_data_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if root:
        return Path(root) / "MRRC-FT710"
    return Path.home() / ".mrrc-ft710"


def config_path() -> Path:
    return user_data_dir() / "ft710.env"


def default_config_path() -> Path:
    return app_dir() / "windows" / "default.env"


def ensure_config() -> Path:
    data_dir = user_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    path = config_path()
    if not path.exists():
        default = default_config_path()
        if default.exists():
            path.write_text(default.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            path.write_text(
                "FT710_WEB_HOST=127.0.0.1\n"
                "FT710_WEB_PORT=8888\n"
                "FT710_SERIAL_PORT=COM3\n",
                encoding="utf-8",
            )
    return path


def load_env(path: Path) -> dict[str, str]:
    env = os.environ.copy()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    env.setdefault("FT710_MEM_FILE", str(user_data_dir() / "mem_channels.json"))
    env.setdefault("FT710_FTDI_LIB_DIR", str(app_dir() / "vendor" / "ftdi" / "windows" / "bin" / "x64"))
    ftdi_dir = Path(env["FT710_FTDI_LIB_DIR"].replace("\\", os.sep))
    if not ftdi_dir.is_absolute():
        env["FT710_FTDI_LIB_DIR"] = str(app_dir() / ftdi_dir)
    return env


def server_executable() -> Path:
    exe = app_dir() / "ft710-server.exe"
    if exe.exists():
        return exe
    return app_dir() / "server.py"


def build_command() -> list[str]:
    server = server_executable()
    if server.suffix.lower() == ".exe":
        return [str(server), "--no-ssl"]
    return [sys.executable, str(server), "--no-ssl"]


def stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def main() -> int:
    cfg = ensure_config()
    env = load_env(cfg)
    port = env.get("FT710_WEB_PORT", DEFAULT_PORT)
    host = env.get("FT710_WEB_HOST", "127.0.0.1")
    url_host = "127.0.0.1" if host in ("::", "0.0.0.0", "") else host
    url = f"http://{url_host}:{port}"

    print(APP_NAME)
    print(f"Config: {cfg}")
    print(f"URL:    {url}")
    print("Close this window or press Ctrl-C to stop the server.")

    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    proc = subprocess.Popen(
        build_command(),
        cwd=str(app_dir()),
        env=env,
        creationflags=creationflags,
    )
    time.sleep(2.0)
    webbrowser.open(url)
    try:
        return proc.wait()
    except KeyboardInterrupt:
        stop_process(proc)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
