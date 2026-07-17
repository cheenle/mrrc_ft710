import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsPackagingFilesTests(unittest.TestCase):
    def test_pyinstaller_specs_use_repo_root(self):
        for spec in (
            ROOT / "packaging" / "pyinstaller" / "ft710_server.spec",
            ROOT / "packaging" / "pyinstaller" / "scope_pipe.spec",
            ROOT / "packaging" / "pyinstaller" / "ft710_launcher.spec",
        ):
            text = spec.read_text(encoding="utf-8")
            self.assertIn("ROOT = Path(SPECPATH).parents[1]", text)

    def test_build_script_runs_all_packaging_steps(self):
        text = (ROOT / "packaging" / "windows" / "build.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("scope_pipe.spec", text)
        self.assertIn("ft710_server.spec", text)
        self.assertIn("ft710_launcher.spec", text)
        self.assertIn("iscc packaging\\windows\\MRRC-FT710.iss", text)


if __name__ == "__main__":
    unittest.main()
