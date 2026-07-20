import socket
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

from windows import launcher


class WindowsLauncherTests(unittest.TestCase):
    def test_load_env_makes_ftdi_dir_absolute(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = tmp_path / "ft710.env"
            config.write_text(
                "FT710_FTDI_LIB_DIR=vendor\\ftdi\\windows\\bin\\x64\n",
                encoding="utf-8",
            )
            app_root = tmp_path / "app"
            with patch.object(launcher, "app_dir", return_value=app_root):
                env = launcher.load_env(config)

        self.assertEqual(
            Path(env["FT710_FTDI_LIB_DIR"]),
            app_root / "vendor" / "ftdi" / "windows" / "bin" / "x64",
        )


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass  # silence request logging


class WaitForServerTests(unittest.TestCase):
    class _RunningProcess:
        def poll(self):
            return None

    class _ExitedProcess:
        def poll(self):
            return 1

    def test_returns_true_once_server_answers_http(self):
        srv = HTTPServer(("127.0.0.1", 0), _HealthHandler)
        port = srv.server_address[1]
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        try:
            self.assertTrue(
                launcher.wait_for_server(f"http://127.0.0.1:{port}", self._RunningProcess(),
                                         timeout_s=5.0)
            )
        finally:
            srv.shutdown()
            thread.join()

    def test_returns_false_when_process_exits_before_server_answers(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            closed_port = probe.getsockname()[1]
        self.assertFalse(
            launcher.wait_for_server(f"http://127.0.0.1:{closed_port}", self._ExitedProcess(),
                                     timeout_s=5.0)
        )


if __name__ == "__main__":
    unittest.main()
