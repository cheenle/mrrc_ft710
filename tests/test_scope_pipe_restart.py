import unittest
from unittest.mock import patch

try:
    import server
except ImportError:
    server = None


class FakePipeStream:
    async def read(self, _n):
        return b""

    async def readline(self):
        return b""


class FakePipeProcess:
    pid = 12345
    returncode = 1

    def __init__(self):
        self.stdout = FakePipeStream()
        self.stderr = FakePipeStream()


@unittest.skipIf(server is None, "fastapi not available in test environment")
class ScopePipeRestartTests(unittest.IsolatedAsyncioTestCase):
    async def test_exited_scope_pipe_can_restart_while_current_reader_task_is_finishing(self):
        old_clients = server.spectrum_clients
        old_read_task = server._scope_read_task
        old_proc = server._scope_proc
        old_scope = server.scope
        old_lock = server._scope_pipe_lock
        started = []

        async def no_sleep(_seconds):
            return None

        async def fake_create_subprocess_exec(*_args, **_kwargs):
            started.append(True)
            return FakePipeProcess()

        proc = FakePipeProcess()
        server.spectrum_clients = {object()}
        server._scope_read_task = None
        server._scope_proc = proc
        server.scope = None
        server._scope_pipe_lock = None

        async def run_reader_as_tracked_task():
            server._scope_read_task = server.asyncio.current_task()
            await server._read_scope_pipe(proc)

        try:
            with (
                patch.object(server, "_scope_pipe_command", return_value=["scope_pipe"]),
                patch.object(server.asyncio, "sleep", no_sleep),
                patch.object(server.asyncio, "create_subprocess_exec", fake_create_subprocess_exec),
            ):
                await run_reader_as_tracked_task()
        finally:
            server.spectrum_clients = old_clients
            server._scope_read_task = old_read_task
            server._scope_proc = old_proc
            server.scope = old_scope
            server._scope_pipe_lock = old_lock

        self.assertEqual(len(started), 1)


if __name__ == "__main__":
    unittest.main()
