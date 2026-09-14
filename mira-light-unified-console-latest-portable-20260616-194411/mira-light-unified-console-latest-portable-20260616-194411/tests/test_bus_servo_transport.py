from __future__ import annotations

import socketserver
import threading
import unittest

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from bus_servo_transport import BusServoRuntimeConfig, BusServoTransportError, TcpBusServoTransport  # noqa: E402


class _OneShotHandler(socketserver.BaseRequestHandler):
    response = b""

    def handle(self) -> None:
        self.request.recv(4096)
        if self.response:
            self.request.sendall(self.response)


class TcpBusServoTransportTests(unittest.TestCase):
    def run_server(self, response: bytes):
        class Handler(_OneShotHandler):
            pass

        Handler.response = response
        server = socketserver.TCPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.handle_request, daemon=True)
        thread.start()
        return server, thread

    def test_send_requires_ok_ack_by_default(self) -> None:
        server, thread = self.run_server(b"")
        try:
            transport = TcpBusServoTransport("127.0.0.1", server.server_address[1], timeout_seconds=0.5)

            with self.assertRaisesRegex(BusServoTransportError, "did not acknowledge"):
                transport.send("#003P1500T0100!")
        finally:
            thread.join(timeout=1)
            server.server_close()

    def test_send_accepts_ok_ack(self) -> None:
        server, thread = self.run_server(b"OK,#003P1500T0100!,15\n")
        try:
            transport = TcpBusServoTransport("127.0.0.1", server.server_address[1], timeout_seconds=0.5)

            result = transport.send("#003P1500T0100!")
        finally:
            thread.join(timeout=1)
            server.server_close()

        self.assertTrue(result["ok"])
        self.assertEqual(result["response"], "OK,#003P1500T0100!,15")

    def test_runtime_config_defaults_to_current_board_and_requires_ack(self) -> None:
        config = BusServoRuntimeConfig.from_file()

        self.assertEqual(config.tcp_host, "192.168.0.183")
        self.assertTrue(config.require_ack)


if __name__ == "__main__":
    unittest.main()
