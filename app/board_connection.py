
import os
import subprocess
import threading
import time
from pathlib import Path

import serial
from serial.tools import list_ports

SIM_PROGRAM = Path(__file__).parent.parent / "firmware" / "demo" / "board_sim"
if os.name == "nt":
    SIM_PROGRAM = SIM_PROGRAM.with_suffix(".exe")
SIM_SCREEN = Path(__file__).parent.parent / "data" / "board_sim.log"


class SimPort:
    def __init__(self, name, baud, timeout=None, exclusive=False):
        SIM_SCREEN.parent.mkdir(parents=True, exist_ok=True)
        self.screen = open(SIM_SCREEN, "a")
        self.program = subprocess.Popen([str(SIM_PROGRAM)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.screen)
        self.program.stdout.readline()

    def write(self, data):
        self.program.stdin.write(data)
        self.program.stdin.flush()

    def readline(self):
        return self.program.stdout.readline()

    def close(self):
        self.program.kill()
        self.program.wait()
        self.screen.close()


class BoardConnection:

    def __init__(self, open_port=serial.Serial, simulated=False):
        self.open_port = open_port
        self.simulated = simulated
        if simulated:
            self.open_port = SimPort
        self.port = None
        self.lock = threading.Lock()
        self.board_number = None
        self.first_note = None
        self.last_note = None

    @property
    def connected(self):
        return self.port is not None

    def find_ports(self):
        names = []
        for port in list_ports.comports():
            if "usbmodem" in port.device or "ttyACM" in port.device or port.device.startswith("COM"):
                names.append(port.device)
        return names

    def connect(self, port_names=None):
        self.disconnect()
        if port_names is None:
            if self.simulated:
                port_names = ["simulator"]
            else:
                port_names = self.find_ports()

        for name in port_names:
            try:
                port = self.open_port(name, 115200, timeout=1, exclusive=True)
            except (serial.SerialException, OSError):
                continue

            try:
                port.write(b"HELLO\n")
                reply = port.readline().decode(errors="replace").strip()
            except (serial.SerialException, OSError):
                reply = ""
            parts = reply.split()

            if len(parts) == 6 and parts[:3] == ["ID", "SHAHMATION", "KEY"] and all(p.isdigit() for p in parts[3:]):
                self.port = port
                self.board_number = int(parts[3])
                self.first_note = int(parts[4])
                self.last_note = int(parts[5])
                return
            port.close()

        if self.simulated:
            raise ConnectionError("Simulator isn't built, run firmware/demo/build_sim.sh")
        raise ConnectionError("No ShahMation board found")

    def close_port(self):
        if self.port is not None:
            try:
                self.port.close()
            except (serial.SerialException, OSError):
                pass
        self.port = None

    def disconnect(self):
        with self.lock:
            self.close_port()

    def send(self, line):
        with self.lock:
            if self.port is None:
                raise ConnectionError("Board is not connected")
            try:
                self.port.write((line + "\n").encode())
                reply = self.port.readline().decode(errors="replace").strip()
            except (serial.SerialException, OSError):
                reply = ""
            if reply == "":
                self.close_port()
                raise ConnectionError("Lost the board")
            return reply

    def send_checked(self, line):
        reply = self.send(line)
        if reply.startswith("ERR"):
            raise ValueError("Board said: " + reply)
        return reply

    def note_on(self, note, velocity):
        return self.send_checked("ON " + str(note) + " " + str(velocity))

    def note_off(self, note):
        return self.send_checked("OFF " + str(note))

    def all_off(self):
        return self.send_checked("ALLOFF")

    def ping(self):
        return self.send_checked("PING")

    def test_note(self, note):
        self.note_on(note, 64)
        time.sleep(0.3)
        self.note_off(note)

    def panic(self):
        try:
            self.send("ALLOFF")
        except ConnectionError:
            pass
        self.disconnect()
