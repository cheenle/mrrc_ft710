import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import scope_libraries
import server


class WindowsPackagingPathTests(unittest.TestCase):
    def test_resource_roots_include_pyinstaller_meipass(self):
        fake_meipass = Path("/tmp/ft710_meipass")
        with patch.object(sys, "_MEIPASS", str(fake_meipass), create=True):
            roots = scope_libraries.get_resource_roots()
        self.assertIn(fake_meipass, roots)

    def test_resource_roots_include_frozen_executable_dir(self):
        fake_exe = "/tmp/ft710_app/ft710-server.exe"
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "executable", fake_exe),
        ):
            roots = scope_libraries.get_resource_roots()
        self.assertIn(Path("/tmp/ft710_app").resolve(), roots)

    def test_windows_vendor_dir_is_searched(self):
        with patch.object(scope_libraries.sys, "platform", "win32"):
            dirs = scope_libraries.get_candidate_library_dirs()
        expected_suffix = ("vendor", "ftdi", "windows", "bin", "x64")
        self.assertTrue(
            any(path.parts[-len(expected_suffix):] == expected_suffix for path in dirs)
        )

    def test_configure_windows_dll_search_path_calls_add_dll_directory(self):
        calls = []

        def fake_add_dll_directory(path):
            calls.append(Path(path))
            return object()

        with (
            patch.object(scope_libraries.sys, "platform", "win32"),
            patch.object(
                scope_libraries.os,
                "add_dll_directory",
                fake_add_dll_directory,
                create=True,
            ),
            patch.object(
                scope_libraries,
                "get_candidate_library_dirs",
                return_value=[Path("/tmp/missing"), Path("/tmp/exists")],
            ),
            patch.object(Path, "is_dir", lambda self: self == Path("/tmp/exists")),
        ):
            scope_libraries.configure_windows_dll_search_path()

        self.assertEqual(calls, [Path("/tmp/exists")])


class BundledDataDirTests(unittest.TestCase):
    def test_uses_meipass_when_set(self):
        fake_meipass = Path("/tmp/ft710_meipass")
        with patch.object(sys, "_MEIPASS", str(fake_meipass), create=True):
            self.assertEqual(server._bundled_data_dir(), fake_meipass)

    def test_falls_back_to_runtime_dir_without_meipass(self):
        self.assertFalse(hasattr(sys, "_MEIPASS"))
        self.assertEqual(server._bundled_data_dir(), server._runtime_dir())


class StopProcGracefullyTests(unittest.IsolatedAsyncioTestCase):
    """Windows can't deliver SIGTERM to a subprocess via terminate() — it calls
    TerminateProcess(), which kills immediately and skips the child's cleanup
    (e.g. FT_Close on an FT4222 handle). CTRL_BREAK_EVENT is the only signal a
    Windows child can actually catch, so _stop_proc_gracefully must prefer it
    there instead of terminate()."""

    async def test_sends_ctrl_break_on_windows(self):
        proc = MagicMock()
        proc.wait = AsyncMock(return_value=None)
        with (
            patch.object(server.sys, "platform", "win32"),
            patch.object(server.signal, "CTRL_BREAK_EVENT", 21, create=True),
        ):
            await server._stop_proc_gracefully(proc)
        proc.send_signal.assert_called_once_with(21)
        proc.terminate.assert_not_called()

    async def test_uses_terminate_on_posix(self):
        proc = MagicMock()
        proc.wait = AsyncMock(return_value=None)
        with patch.object(server.sys, "platform", "darwin"):
            await server._stop_proc_gracefully(proc)
        proc.terminate.assert_called_once()
        proc.send_signal.assert_not_called()


class ScopePipeCommandTests(unittest.TestCase):
    def test_unfrozen_scope_pipe_command_uses_python_script(self):
        cmd = server._scope_pipe_command()
        self.assertIsNotNone(cmd)
        assert cmd is not None
        self.assertEqual(Path(cmd[1]).name, "scope_pipe.py")

    def test_frozen_scope_pipe_command_uses_bundled_exe(self):
        with (
            patch.object(server.sys, "frozen", True, create=True),
            patch.object(server.sys, "platform", "win32"),
            patch.object(server.sys, "executable", r"C:\MRRC-FT710\ft710-server.exe"),
            patch.object(server.Path, "exists", lambda self: self.name == "scope_pipe.exe"),
        ):
            cmd = server._scope_pipe_command()
        self.assertIsNotNone(cmd)
        assert cmd is not None
        self.assertEqual(Path(cmd[0]).name, "scope_pipe.exe")


if __name__ == "__main__":
    unittest.main()
