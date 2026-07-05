import unittest

import server


class FakeCat:
    connected = True

    def __init__(self):
        self.commands = []
        self.serial = None   # Will be checked by getattr

    async def send_command(self, cmd):
        self.commands.append(cmd)
        return "OK"

    async def connect(self):
        self.connected = True


class FakeSerial:
    is_open = True


class ServerScopeInitTests(unittest.IsolatedAsyncioTestCase):
    async def test_scope_init_sends_cat_commands(self):
        old_cat = server.cat
        fake = FakeCat()
        fake.serial = FakeSerial()  # Simulate open serial port
        server.cat = fake
        try:
            await server._init_scope_cat()
        finally:
            server.cat = old_cat

        # Should send both scope init commands
        self.assertEqual(fake.commands, ["EX040101", "EX040200"])

    async def test_scope_init_skips_when_no_serial(self):
        old_cat = server.cat
        fake = FakeCat()
        fake.serial = None  # No serial port
        server.cat = fake
        try:
            await server._init_scope_cat()
        finally:
            server.cat = old_cat

        # Should not send any commands when serial is absent
        self.assertEqual(fake.commands, [])


if __name__ == "__main__":
    unittest.main()
