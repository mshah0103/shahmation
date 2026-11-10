
import hashlib
import tempfile
import time
import unittest
from pathlib import Path

import mido

from player import Player


class FakeBoard:
    def __init__(self):
        self.connected = True
        self.first_note = 21
        self.last_note = 36
        self.sent = []
        self.lose_connection = False

    def note_on(self, note, velocity):
        if self.lose_connection:
            raise ConnectionError("Lost the board")
        self.sent.append("ON " + str(note) + " " + str(velocity))

    def note_off(self, note):
        self.sent.append("OFF " + str(note))

    def all_off(self):
        self.sent.append("ALLOFF")

    def ping(self):
        self.sent.append("PING")
        return "PONG"


def write_song(path, events):
    song = mido.MidiFile()
    track = mido.MidiTrack()
    for kind, note, ticks in events:
        track.append(mido.Message(kind, note=note, velocity=64, time=ticks))
    song.tracks.append(track)
    song.save(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PlayerTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.board = FakeBoard()
        self.player = Player(self.board)

    def tearDown(self):
        self.player.stop()
        self.temp.cleanup()

    def play_and_wait(self, events):
        path = self.folder / "song.mid"
        sha = write_song(path, events)
        self.player.play(path, sha, "Test Song")
        self.player.thread.join(10)

    def test_tc_p04_plays_in_order_then_releases(self):
        self.play_and_wait([
            ("note_on", 30, 0), ("note_off", 30, 48),
            ("note_on", 32, 0), ("note_off", 32, 48),
        ])
        self.assertEqual(self.board.sent, ["ON 30 64", "OFF 30", "ON 32 64", "OFF 32", "ALLOFF"])
        self.assertEqual(self.player.status()["state"], "idle")

    def test_out_of_range_notes_skipped(self):
        self.play_and_wait([("note_on", 60, 0), ("note_on", 22, 10), ("note_off", 60, 10), ("note_off", 22, 10)])
        self.assertEqual(self.board.sent, ["ON 22 64", "OFF 22", "ALLOFF"])

    def test_long_rest_sends_ping(self):
        self.play_and_wait([("note_on", 30, 0), ("note_off", 30, 1150)])
        self.assertIn("PING", self.board.sent)
        self.assertEqual(self.board.sent[-2:], ["OFF 30", "ALLOFF"])

    def test_tc_p07_stop_releases_and_sends_nothing_more(self):
        path = self.folder / "song.mid"
        sha = write_song(path, [("note_on", 30, 0), ("note_off", 30, 2880)])
        self.player.play(path, sha, "Long")
        time.sleep(0.3)
        self.player.stop()
        self.assertEqual(self.board.sent[-1], "ALLOFF")
        self.assertNotIn("OFF 30", self.board.sent)
        sent_at_stop = len(self.board.sent)
        time.sleep(0.6)
        self.assertEqual(len(self.board.sent), sent_at_stop)
        self.assertEqual(self.player.status()["state"], "idle")

    def test_tc_p05_pause_and_resume(self):
        path = self.folder / "song.mid"
        sha = write_song(path, [("note_on", 30, 0), ("note_off", 30, 384), ("note_on", 32, 0), ("note_off", 32, 48)])
        self.player.play(path, sha, "Pause Me")
        time.sleep(0.1)
        self.player.pause()
        self.assertEqual(self.player.status()["state"], "paused")
        self.assertEqual(self.board.sent, ["ON 30 64", "ALLOFF"])
        time.sleep(0.8)
        self.assertNotIn("ON 32 64", self.board.sent)
        self.player.resume()
        self.player.thread.join(10)
        self.assertEqual(self.board.sent.count("ON 30 64"), 1)
        self.assertEqual(self.board.sent.count("ON 32 64"), 1)
        self.assertEqual(self.board.sent[-1], "ALLOFF")

    def test_tc_r01_missing_or_changed_file_blocked(self):
        with self.assertRaises(ValueError):
            self.player.play(self.folder / "nope.mid", "abc", "Missing")
        path = self.folder / "song.mid"
        write_song(path, [("note_on", 30, 0)])
        with self.assertRaises(ValueError):
            self.player.play(path, "0" * 64, "Changed")
        bad = self.folder / "bad.mid"
        bad.write_bytes(b"not midi")
        with self.assertRaises(ValueError):
            self.player.play(bad, hashlib.sha256(b"not midi").hexdigest(), "Bad")
        self.assertEqual(self.board.sent, [])

    def test_needs_connected_board(self):
        self.board.connected = False
        path = self.folder / "song.mid"
        sha = write_song(path, [("note_on", 30, 0)])
        with self.assertRaises(ValueError):
            self.player.play(path, sha, "No Board")
        self.assertEqual(self.board.sent, [])

    def test_lost_board_shows_error(self):
        self.board.lose_connection = True
        self.play_and_wait([("note_on", 30, 0), ("note_off", 30, 48)])
        status = self.player.status()
        self.assertEqual(status["state"], "idle")
        self.assertEqual(status["error"], "Lost the board")

    def test_slow_board_doesnt_make_song_late(self):
        def slow_note_on(note, velocity):
            time.sleep(0.005)
            self.board.sent.append("ON " + str(note) + " " + str(velocity))
        self.board.note_on = slow_note_on
        events = []
        for i in range(40):
            events.append(("note_on", 30, 24))
        start = time.time()
        self.play_and_wait(events)
        self.assertLess(time.time() - start, 1.12)


if __name__ == "__main__":
    unittest.main()
