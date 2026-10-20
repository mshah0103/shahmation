from pathlib import Path
from starlette.applications import Starlette
from starlette.responses import FileResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

STATIC = Path(__file__).parent / "static"

async def home(request):
    return FileResponse(STATIC / "index.html")

app = Starlette(routes=[
    Route("/", home),
    Mount("/static", StaticFiles(directory=STATIC), name="static"),
])