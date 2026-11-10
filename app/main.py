import os
import sqlite3
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from board_connection import BoardConnection
from music_library import MusicLibrary, MAX_UPLOAD_BYTES
from player import Player

STATIC = Path(__file__).parent / "static"
ROOT = Path(__file__).parent.parent
MIDI_FOLDER = ROOT / "ShahMation Midi Library"

# open the music database and add any songs from the index not yet added
# first run reads every midi file after that it's instant
library = MusicLibrary(ROOT / "data" / "music.db", MIDI_FOLDER, ROOT / "data" / "personal")
print("Added", library.load_index(MIDI_FOLDER / "LIBRARY_INDEX.csv"), "songs")

simulated = os.environ.get("SHAHMATION_SIM") == "1"
board = BoardConnection(simulated=simulated)
if simulated:
    print("Simulator mode: Connect will use the pretend board")
player = Player(board)


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



def board_info():
    return {
        "connected": board.connected,
        "board_number": board.board_number,
        "first_note": board.first_note,
        "last_note": board.last_note,
        "simulated": board.simulated,
    }


def board_status(request):
    return JSONResponse(board_info())


def board_connect(request):
    player.stop()
    try:
        board.connect()
    except ConnectionError as e:
        return JSONResponse({"error": str(e)}, status_code=503)
    return JSONResponse(board_info())


def board_test(request):
    try:
        note = int(request.query_params.get("note", ""))
    except ValueError:
        return JSONResponse({"error": "Type a note number"}, status_code=400)
    if not board.connected:
        return JSONResponse({"error": "Connect the board first"}, status_code=400)
    if note < board.first_note or note > board.last_note:
        return JSONResponse({"error": "This board plays notes " + str(board.first_note) + " to " + str(board.last_note)}, status_code=400)
    if player.state != "idle":
        return JSONResponse({"error": "Stop the song first"}, status_code=400)
    try:
        board.test_note(note)
    except (ConnectionError, ValueError) as e:
        return JSONResponse({"error": str(e)}, status_code=503)
    return JSONResponse({"tested": note})


def panic(request):
    player.stop()
    board.panic()
    return JSONResponse(board_info())


def player_status(request):
    return JSONResponse(player.status())


async def play(request):
    try:
        song = library.get(int(request.query_params.get("music_id", "")))
    except (ValueError, sqlite3.Error):
        song = None
    if song is None:
        return JSONResponse({"error": "Couldn't find that song"}, status_code=400)
    try:
        player.play(library.file_path(song), song.sha256, song.title)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return JSONResponse(player.status())


def pause(request):
    try:
        player.pause()
    except (ConnectionError, ValueError):
        pass
    return JSONResponse(player.status())


def resume(request):
    player.resume()
    return JSONResponse(player.status())


def stop(request):
    player.stop()
    return JSONResponse(player.status())


app = Starlette(routes=[
    Route("/", home),
    Route("/api/songs", songs),
    Route("/api/songs/upload", upload, methods=["POST"]),
    Route("/api/board", board_status),
    Route("/api/board/connect", board_connect, methods=["POST"]),
    Route("/api/board/test", board_test, methods=["POST"]),
    Route("/api/panic", panic, methods=["POST"]),
    Route("/api/player", player_status),
    Route("/api/play", play, methods=["POST"]),
    Route("/api/pause", pause, methods=["POST"]),
    Route("/api/resume", resume, methods=["POST"]),
    Route("/api/stop", stop, methods=["POST"]),
    Mount("/static", StaticFiles(directory=STATIC), name="static"),
])
