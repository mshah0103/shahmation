
import unittest
from unittest import mock

import board_connection
from board_connection import BoardConnection, SIM_PROGRAM, SIM_SCREEN


class FakePort:
    def __init__(self, name, baud, timeout=None, exclusive=False):
        self.name = name
        self.exclusive = exclusive
        self.lines = []
        self.replies = []
        self.closed = False
        self.hello_reply = "ID SHAHMATION KEY 1 21 36"
        self.silent = False

    def write(self, data):
        line = data.decode().strip()
        self.lines.append(line)
        if line == "HELLO":
            self.replies.append(self.hello_reply)
        elif line == "PING":
            self.replies.append("PONG")
        elif line.startswith("ON 99"):
            self.replies.append("ERR note out of range")
        else:
            self.replies.append("OK")

    def readline(self):
        if self.silent or not self.replies:
            return b""
        return (self.replies.pop(0) + "\n").encode()

    def close(self):
        self.closed = True


class BoardConnectionTests(unittest.TestCase):

    def setUp(self):
        self.ports = []
        self.wrong_names = []

        def open_port(name, baud, timeout=None, exclusive=False):
            port = FakePort(name, baud, timeout, exclusive)
            if name in self.wrong_names:
                port.hello_reply = "hi im an arduino"
            self.ports.append(port)
            return port

        self.board = BoardConnection(open_port=open_port)

    def test_tc_p03_connect_checks_identity_and_plays_nothing(self):
        self.board.connect(["fake"])
        self.assertTrue(self.board.connected)
        self.assertEqual(self.board.board_number, 1)
        self.assertEqual(self.board.first_note, 21)
        self.assertEqual(self.board.last_note, 36)
        self.assertEqual(self.ports[0].lines, ["HELLO"])
        self.assertTrue(self.ports[0].exclusive)

    def test_tc_r05_wrong_board_rejected(self):
        self.wrong_names = ["other"]
        with self.assertRaises(ConnectionError):
            self.board.connect(["other"])
        self.assertFalse(self.board.connected)
        self.assertTrue(self.ports[0].closed)

    def test_skips_wrong_port_finds_right_one(self):
        self.wrong_names = ["other"]
        self.board.connect(["other", "pico"])
        self.assertTrue(self.board.connected)
        self.assertTrue(self.ports[0].closed)
        self.assertFalse(self.ports[1].closed)

    def test_busy_port_skipped(self):
        def busy(name, baud, timeout=None, exclusive=False):
            raise OSError("port is busy")
        board = BoardConnection(open_port=busy)
        with self.assertRaises(ConnectionError):
            board.connect(["busy"])

    def test_notes_and_ping(self):
        self.board.connect(["fake"])
        self.board.note_on(30, 100)
        self.board.note_off(30)
        self.assertEqual(self.board.ping(), "PONG")
        self.assertEqual(self.ports[0].lines, ["HELLO", "ON 30 100", "OFF 30", "PING"])

    def test_error_reply_raises(self):
        self.board.connect(["fake"])
        with self.assertRaises(ValueError):
            self.board.note_on(99, 64)

    def test_tc_p07_panic_releases_and_disconnects(self):
        self.board.connect(["fake"])
        self.board.panic()
        self.assertEqual(self.ports[0].lines[-1], "ALLOFF")
        self.assertTrue(self.ports[0].closed)
        self.assertFalse(self.board.connected)
        with self.assertRaises(ConnectionError):
            self.board.note_on(30, 64)

    def test_panic_when_not_connected_is_fine(self):
        self.board.panic()
        self.assertFalse(self.board.connected)

    def test_tc_r15_no_reply_means_lost(self):
        self.board.connect(["fake"])
        self.ports[0].silent = True
        with self.assertRaises(ConnectionError):
            self.board.ping()
        self.assertFalse(self.board.connected)

    def test_find_ports_mac_pi_and_windows(self):
        class Port:
            def __init__(self, device):
                self.device = device
        ports = [Port("/dev/cu.usbmodem1101"), Port("/dev/ttyACM0"), Port("COM3"), Port("/dev/cu.Bluetooth-Incoming-Port")]
        with mock.patch.object(board_connection.list_ports, "comports", return_value=ports):
            self.assertEqual(self.board.find_ports(), ["/dev/cu.usbmodem1101", "/dev/ttyACM0", "COM3"])

    def test_one_note_test(self):
        self.board.connect(["fake"])
        self.board.test_note(25)
        self.assertEqual(self.ports[0].lines[1:], ["ON 25 64", "OFF 25"])



@unittest.skipUnless(SIM_PROGRAM.exists(), "simulator not built")
class SimulatedBoardTests(unittest.TestCase):

    def setUp(self):
        self.board = BoardConnection(simulated=True)

    def tearDown(self):
        self.board.disconnect()

    def test_connects_to_firmware_code(self):
        self.board.connect()
        self.assertTrue(self.board.connected)
        self.assertTrue(self.board.simulated)
        self.assertEqual((self.board.first_note, self.board.last_note), (21, 108))

    def test_notes_and_errors_come_from_firmware(self):
        self.board.connect()
        self.assertEqual(self.board.note_on(60, 100), "OK")
        self.assertEqual(self.board.note_off(60), "OK")
        with self.assertRaises(ValueError):
            self.board.note_on(109, 100)

    def test_panic_disconnects(self):
        self.board.connect()
        self.board.panic()
        self.assertFalse(self.board.connected)
        self.assertIn("ALLOFF", SIM_SCREEN.read_text())


if __name__ == "__main__":
    unittest.main()
