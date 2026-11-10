# tests for the music database
# each test is named after the test case
# run from the app folder with: python -m unittest -v

import io
import sqlite3
import tempfile
import unittest
from pathlib import Path

import mido

import music_library
from music_library import MusicLibrary, MAX_UPLOAD_BYTES


def make_midi(path):
    # makes a midi file with one note so mido can read it
    path.parent.mkdir(parents=True, exist_ok=True)
    song = mido.MidiFile()
    track = mido.MidiTrack()
    track.append(mido.Message("note_on", note=60, velocity=64, time=0))
    track.append(mido.Message("note_off", note=60, velocity=64, time=480))
    song.tracks.append(track)
    song.save(path)


def midi_bytes(note=60):
    # same as make_midi but gives back the bytes like an upload would
    song = mido.MidiFile()
    track = mido.MidiTrack()
    track.append(mido.Message("note_on", note=note, velocity=64, time=0))
    track.append(mido.Message("note_off", note=note, velocity=64, time=480))
    song.tracks.append(track)
    buffer = io.BytesIO()
    song.save(file=buffer)
    return buffer.getvalue()


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
        # junk file that isn't midi
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
        self.personal = folder / "personal"
        self.library = MusicLibrary(self.db_path, self.lib_folder, self.personal)

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
        self.library = MusicLibrary(self.db_path, self.lib_folder, self.personal)
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

    def test_tc_p02_add_survives_restart(self):
        item = self.library.add("My Song.mid", midi_bytes())
        self.assertEqual(item.source_kind, "personal")
        self.assertEqual(item.title, "My Song")
        self.assertIsNone(item.composer)
        self.assertGreater(item.duration_seconds, 0)
        self.assertTrue((self.personal / "My Song.mid").exists())

        # reopen like the app restarted
        self.library.close()
        self.library = MusicLibrary(self.db_path, self.lib_folder, self.personal)
        self.assertEqual(self.library.search("my song")[0].music_id, item.music_id)

    def test_tc_r01_rejects_bad_files(self):
        # real midi file but nothing plays
        no_notes = mido.MidiFile()
        no_notes.tracks.append(mido.MidiTrack([mido.MetaMessage("end_of_track", time=0)]))
        buffer = io.BytesIO()
        no_notes.save(file=buffer)

        bad_uploads = [
            ("x.mid", b""),
            ("x.mid", b"not midi"),
            ("x.txt", midi_bytes()),
            ("x.mid", b"0" * (MAX_UPLOAD_BYTES + 1)),
            ("x.mid", buffer.getvalue()),
        ]
        for name, data in bad_uploads:
            with self.assertRaises(ValueError):
                self.library.add(name, data)
            self.assertEqual(self.library.count(""), 0)
            self.assertEqual(list(self.personal.iterdir()), [])

    def test_tc_r02_name_stays_in_folder(self):
        item = self.library.add("../../evil.mid", midi_bytes())
        self.assertEqual(item.relative_path, "evil.mid")
        self.assertTrue((self.personal / "evil.mid").exists())

        item = self.library.add("'; DROP TABLE music_item; --.mid", midi_bytes(62))
        # the underscore turns into a space
        self.assertEqual(item.title, "'; DROP TABLE music item; --")
        self.assertEqual(self.library.count(""), 2)

    def test_tc_r03_duplicate_upload(self):
        self.library.add("a.mid", midi_bytes())
        # same name different song
        with self.assertRaises(ValueError):
            self.library.add("a.mid", midi_bytes(62))
        # different name same song
        with self.assertRaises(ValueError):
            self.library.add("b.mid", midi_bytes())
        self.assertEqual(self.library.count(""), 1)
        # file already on disk that the db doesn't know about
        (self.personal / "old.mid").write_bytes(b"old")
        with self.assertRaises(ValueError):
            self.library.add("old.mid", midi_bytes(65))
        self.assertEqual((self.personal / "old.mid").read_bytes(), b"old")

    def test_uppercase_extension_ok(self):
        self.assertEqual(self.library.add("SONG.MID", midi_bytes()).title, "SONG")
        self.assertEqual(self.library.add("tune.midi", midi_bytes(64)).title, "tune")

    def test_tc_r04_failed_save_rolls_back(self):
        # personal is a plain file now so saving can't work
        self.personal.rmdir()
        self.personal.write_text("x")
        with self.assertRaises(OSError):
            self.library.add("a.mid", midi_bytes())
        self.assertEqual(self.library.count(""), 0)

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            self.library.add(".mid", midi_bytes())
        with self.assertRaises(ValueError):
            self.library.add("   .mid", midi_bytes())

    def test_get_and_file_path(self):
        self.library.load_index(self.csv_path)
        song = self.library.search("maple")[0]
        self.assertEqual(self.library.get(song.music_id).title, "Maple Leaf Rag")
        self.assertTrue(self.library.file_path(song).exists())
        mine = self.library.add("Mine.mid", midi_bytes(70))
        self.assertEqual(self.library.file_path(mine), self.personal / "Mine.mid")
        self.assertIsNone(self.library.get(99999))


if __name__ == "__main__":
    unittest.main()
