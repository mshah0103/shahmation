# music database for ShahMation
# all sql lives in this document

import csv
import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import mido

# save to the database every 500 songs to make sure interrupts don't impact load
BATCH_SIZE = 500


# one row of the music_item table
@dataclass
class MusicItem:
    music_id: int
    source_kind: str  # "library" or "personal"
    relative_path: str
    title: str
    composer: str | None
    duration_seconds: float | None
    sha256: str | None
    added_at: str


class MusicLibrary:

    def __init__(self, db_path, library_folder):
        self.library_folder = Path(library_folder)

        # make the data folder if this is the first run
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # lets me do row["title"]

        # IF NOT EXISTS so restarts do not wipe
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS music_item (
                music_id INTEGER PRIMARY KEY,
                source_kind TEXT NOT NULL CHECK (source_kind IN ('library', 'personal')),
                relative_path TEXT NOT NULL,
                title TEXT NOT NULL,
                composer TEXT,
                duration_seconds REAL,
                sha256 TEXT,
                added_at TEXT NOT NULL,
                UNIQUE (source_kind, relative_path)
            );
            CREATE INDEX IF NOT EXISTS idx_music_title ON music_item(title);
            CREATE INDEX IF NOT EXISTS idx_music_composer ON music_item(composer);
            CREATE INDEX IF NOT EXISTS idx_music_sha256 ON music_item(sha256);
        """)

    def close(self):
        self.conn.close()

    def load_index(self, csv_path):
        # adds every song from LIBRARY_INDEX.csv that isn't in the database yet
        # returns how many songs got added.
        if not Path(csv_path).exists():
            print("Warning: couldn't find", csv_path, "so the library is empty")
            return 0

        # grab the paths that already exist
        rows = self.conn.execute(
            "SELECT relative_path FROM music_item WHERE source_kind = 'library'"
        ).fetchall()
        already_have = set(row["relative_path"] for row in rows)

        added = 0
        # "with self.conn" if anything crashes, the unfinished batch gets thrown out
        with self.conn, open(csv_path, newline="", encoding="utf-8-sig") as file:
            for row in csv.DictReader(file):
                path = row["library_path"]
                if path in already_have:
                    continue

                full_path = self.library_folder / path
                if not full_path.exists():
                    print("Warning: missing file, skipping", path)
                    continue

                data = full_path.read_bytes()
                sha256 = hashlib.sha256(data).hexdigest()

                # some old midi files are broken leave the length blank
                try:
                    length = mido.MidiFile(full_path).length
                except Exception:
                    length = None

                self.conn.execute(
                    "INSERT INTO music_item (source_kind, relative_path, title, composer, "
                    "duration_seconds, sha256, added_at) VALUES ('library', ?, ?, ?, ?, ?, ?)",
                    (path, row["piece"], row["composer"], length, sha256,
                     datetime.now().isoformat(timespec="seconds")),
                )
                added += 1
                if added % BATCH_SIZE == 0:
                    self.conn.commit()
                    print("Loaded", added, "songs so far...")
        return added

    def make_where(self, text):
        # builds the WHERE part for search() and count() so they always match
        # ? placeholders mean whatever the user types is just text
        # it never gets run as SQL
        text = text.strip()
        if text == "":
            return "", []
        pattern = "%" + text + "%"
        return " WHERE title LIKE ? OR composer LIKE ?", [pattern, pattern]

    def search(self, text, limit=200):
        # finds songs where the title or composer has the text in it
        # blank text = every song capped at 200 shown results
        where, params = self.make_where(text)
        rows = self.conn.execute(
            "SELECT * FROM music_item" + where + " ORDER BY composer, title LIMIT ?",
            params + [limit],
        ).fetchall()
        return [MusicItem(**dict(row)) for row in rows]

    def count(self, text):
        # how many songs match in total
        where, params = self.make_where(text)
        return self.conn.execute("SELECT COUNT(*) FROM music_item" + where, params).fetchone()[0]
