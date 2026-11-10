
import hashlib
import io
import threading
import time
from pathlib import Path

import mido

PING_EVERY = 0.5


class Player:

    def __init__(self, board):
        self.board = board
        self.thread = None
        self.stopping = threading.Event()
        self.paused = False
        self.state = "idle"
        self.title = None
        self.position = 0.0
        self.length = 0.0
        self.error = None

    def play(self, path, sha256, title):
        if not self.board.connected:
            raise ValueError("Connect the board first")
        path = Path(path)
        if not path.exists():
            raise ValueError("That song's file is missing")
        data = path.read_bytes()
        if sha256 and hashlib.sha256(data).hexdigest() != sha256:
            raise ValueError("That song's file has changed since it was added")
        try:
            song = mido.MidiFile(file=io.BytesIO(data))
        except Exception:
            raise ValueError("That file isn't a valid MIDI file")

        self.stop()
        self.stopping = threading.Event()
        self.paused = False
        self.state = "playing"
        self.title = title
        self.position = 0.0
        self.length = song.length
        self.error = None
        self.thread = threading.Thread(target=self.run, args=(song,), daemon=True)
        self.thread.start()

    def run(self, song):
        try:
            due = time.monotonic()
            for msg in song:
                due += msg.time
                due += self.wait(due - time.monotonic())
                if self.stopping.is_set():
                    break
                self.position += msg.time
                if msg.type not in ("note_on", "note_off"):
                    continue
                if msg.note < self.board.first_note or msg.note > self.board.last_note:
                    continue
                if msg.type == "note_on" and msg.velocity > 0:
                    self.board.note_on(msg.note, msg.velocity)
                else:
                    self.board.note_off(msg.note)
        except (ConnectionError, ValueError) as e:
            self.error = str(e)
        finally:
            try:
                self.board.all_off()
            except (ConnectionError, ValueError):
                pass
            self.state = "idle"

    def wait(self, seconds):
        paused_for = 0
        while not self.stopping.is_set():
            if self.paused:
                started = time.monotonic()
                self.stopping.wait(0.1)
                paused_for += time.monotonic() - started
                continue
            if seconds <= 0:
                return paused_for
            step = min(seconds, PING_EVERY)
            self.stopping.wait(step)
            seconds -= step
            if seconds > 0:
                self.board.ping()
        return paused_for

    def pause(self):
        if self.state == "playing":
            self.paused = True
            self.state = "paused"
            self.board.all_off()

    def resume(self):
        if self.state == "paused":
            self.paused = False
            self.state = "playing"

    def stop(self):
        self.stopping.set()
        if self.thread is not None:
            self.thread.join(2)
        self.paused = False
        self.state = "idle"

    def status(self):
        return {
            "state": self.state,
            "title": self.title,
            "position": round(self.position, 1),
            "length": round(self.length, 1),
            "error": self.error,
        }
