import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
