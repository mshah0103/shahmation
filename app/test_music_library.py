# tests for the music database
# each test is named after the test case
# run from the app folder with: python -m unittest -v

import sqlite3
import tempfile
import unittest
from pathlib import Path

import mido

import music_library
from music_library import MusicLibrary


def make_midi(path):
    # makes a midi file with one note so mido can read it
    path.parent.mkdir(parents=True, exist_ok=True)
    song = mido.MidiFile()
    track = mido.MidiTrack()
    track.append(mido.Message("note_on", note=60, velocity=64, time=0))
    track.append(mido.Message("note_off", note=60, velocity=64, time=480))
    song.tracks.append(track)
    song.save(path)


class MusicLibraryTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        folder = Path(self.temp.name)
        self.lib_folder = folder / "lib"
        self.db_path = folder / "data" / "music.db"
        self.csv_path = folder / "index.csv"

        make_midi(self.lib_folder / "A-D/Claude Debussy/Clair de Lune.mid")
        make_midi(self.lib_folder / "Q-T/Scott Joplin/Maple Leaf Rag.mid")
        make_midi(self.lib_folder / "A-D/Antonín Dvořák/Humoresque.mid")
        # junk file that isn't really midi
        (self.lib_folder / "A-D/Bad").mkdir(parents=True)
        (self.lib_folder / "A-D/Bad/Broken.mid").write_bytes(b"not midi")

        # same columns as the real LIBRARY_INDEX.csv
        # the last row points at a file that doesn't exist
        self.csv_path.write_text(
            "composer,piece,library_path\n"
            "Claude Debussy,Clair de Lune,A-D/Claude Debussy/Clair de Lune.mid\n"
            "Scott Joplin,Maple Leaf Rag,Q-T/Scott Joplin/Maple Leaf Rag.mid\n"
            "Antonín Dvořák,Humoresque,A-D/Antonín Dvořák/Humoresque.mid\n"
            "Bad,Broken,A-D/Bad/Broken.mid\n"
            "Gone,Missing,A-D/Gone/Missing.mid\n",
            encoding="utf-8-sig",
        )
        self.library = MusicLibrary(self.db_path, self.lib_folder)

    def tearDown(self):
        self.library.close()
        self.temp.cleanup()

    def get_row(self, path):
        return self.library.conn.execute(
            "SELECT * FROM music_item WHERE relative_path = ?", (path,)
        ).fetchone()

    def test_tc_r10_data_survives_reopen(self):
        self.assertEqual(self.library.load_index(self.csv_path), 4)
        self.library.close()

        # reopen like the app restarted
        self.library = MusicLibrary(self.db_path, self.lib_folder)
        count = self.library.conn.execute("SELECT COUNT(*) FROM music_item").fetchone()[0]
        self.assertEqual(count, 4)

        tables = self.library.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        self.assertEqual([t[0] for t in tables], ["music_item"])

    def test_tc_r03_no_duplicates(self):
        self.assertEqual(self.library.load_index(self.csv_path), 4)
        self.assertEqual(self.library.load_index(self.csv_path), 0)

    def test_missing_file_skipped(self):
        self.library.load_index(self.csv_path)
        self.assertIsNone(self.get_row("A-D/Gone/Missing.mid"))

    def test_bad_midi_gets_null_length(self):
        self.library.load_index(self.csv_path)
        broken = self.get_row("A-D/Bad/Broken.mid")
        self.assertIsNone(broken["duration_seconds"])
        self.assertEqual(len(broken["sha256"]), 64)

        debussy = self.get_row("A-D/Claude Debussy/Clair de Lune.mid")
        self.assertGreater(debussy["duration_seconds"], 0)

    def test_missing_csv_returns_zero(self):
        self.assertEqual(self.library.load_index("nope.csv"), 0)

    def test_interrupted_load_keeps_finished_batches(self):
        (self.lib_folder / "A-D/Gone/Missing.mid").mkdir(parents=True)
        old_size = music_library.BATCH_SIZE
        music_library.BATCH_SIZE = 3
        try:
            with self.assertRaises(OSError):
                self.library.load_index(self.csv_path)
        finally:
            music_library.BATCH_SIZE = old_size
        self.assertEqual(self.library.count(""), 3)

        (self.lib_folder / "A-D/Gone/Missing.mid").rmdir()
        self.assertEqual(self.library.load_index(self.csv_path), 1)

    def test_tc_p01_search_title_and_composer(self):
        self.library.load_index(self.csv_path)

        results = self.library.search("maple")
        self.assertEqual([song.title for song in results], ["Maple Leaf Rag"])

        self.assertEqual(self.library.search("DEBUSSY")[0].composer, "Claude Debussy")

        self.assertEqual(len(self.library.search("")), 4)
        self.assertEqual(len(self.library.search("   ")), 4)
        self.assertEqual(self.library.count(""), 4)
        self.assertEqual(self.library.count("rag"), 1)
        self.assertEqual(len(self.library.search("", limit=2)), 2)

    def test_tc_r02_code_like_text(self):
        self.library.load_index(self.csv_path)
        self.assertEqual(self.library.search("'; DROP TABLE music_item; --"), [])
        self.assertEqual(self.library.count(""), 4)

    def test_accented_search(self):
        self.library.load_index(self.csv_path)
        self.assertEqual(self.library.search("Dvořák")[0].title, "Humoresque")

    def test_search_order(self):
        self.library.load_index(self.csv_path)
        composers = [song.composer for song in self.library.search("")]
        self.assertEqual(composers, ["Antonín Dvořák", "Bad", "Claude Debussy", "Scott Joplin"])


if __name__ == "__main__":
    unittest.main()
