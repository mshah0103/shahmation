import sqlite3
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from music_library import MusicLibrary, MAX_UPLOAD_BYTES

STATIC = Path(__file__).parent / "static"
ROOT = Path(__file__).parent.parent
MIDI_FOLDER = ROOT / "ShahMation Midi Library"

# open the music database and add any songs from the index not yet added
# first run reads every midi file after that it's instant
library = MusicLibrary(ROOT / "data" / "music.db", MIDI_FOLDER, ROOT / "data" / "personal")
print("Added", library.load_index(MIDI_FOLDER / "LIBRARY_INDEX.csv"), "songs")


# the parts of a song the screen needs
def song_json(song):
    return {
        "music_id": song.music_id,
        "title": song.title,
        "composer": song.composer,
        "duration_seconds": song.duration_seconds,
    }


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
        song_list.append(song_json(song))
    return JSONResponse({"total": total, "songs": song_list})


async def upload(request):
    # the browser sends the raw file as the body and the file name in the url
    name = request.query_params.get("name", "")
    # don't read a huge file
    if int(request.headers.get("content-length", 0)) > MAX_UPLOAD_BYTES:
        return JSONResponse({"error": "That file is too big (2 MB max)"}, status_code=400)
    data = await request.body()
    try:
        song = library.add(name, data)
    except ValueError as e:
        # message is written for the user
        return JSONResponse({"error": str(e)}, status_code=400)
    except (OSError, sqlite3.Error):
        return JSONResponse({"error": "Couldn't save the file"}, status_code=503)
    return JSONResponse(song_json(song), status_code=201)


app = Starlette(routes=[
    Route("/", home),
    Route("/api/songs", songs),
    Route("/api/songs/upload", upload, methods=["POST"]),
    Mount("/static", StaticFiles(directory=STATIC), name="static"),
])
