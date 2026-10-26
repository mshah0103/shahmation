import sqlite3
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from music_library import MusicLibrary

STATIC = Path(__file__).parent / "static"
ROOT = Path(__file__).parent.parent
MIDI_FOLDER = ROOT / "ShahMation MIDI Library"

# open the music database and add any songs from the index not yet added
# first run reads every midi file after that it's instant
library = MusicLibrary(ROOT / "data" / "music.db", MIDI_FOLDER)
print("Added", library.load_index(MIDI_FOLDER / "LIBRARY_INDEX.csv"), "songs")


async def home(request):
    return FileResponse(STATIC / "index.html")


async def songs(request):
    text = request.query_params.get("q", "")
    try:
        found = library.search(text)
        total = library.count(text)
    except sqlite3.Error:
        # in case of db error show:
        return JSONResponse({"error": "Music library is unavailable"}, status_code=503)

    song_list = []
    for song in found:
        song_list.append({
            "music_id": song.music_id,
            "title": song.title,
            "composer": song.composer,
            "duration_seconds": song.duration_seconds,
        })
    return JSONResponse({"total": total, "songs": song_list})


app = Starlette(routes=[
    Route("/", home),
    Route("/api/songs", songs),
    Mount("/static", StaticFiles(directory=STATIC), name="static"),
])
