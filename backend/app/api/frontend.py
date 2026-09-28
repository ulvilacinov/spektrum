from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.exceptions import NotFoundError


def mount_frontend(app: FastAPI, dist_dir: Path, *, api_prefix: str) -> None:
    """Serves the built single-page frontend from ``dist_dir`` next to the API.

    Files that exist are returned as they are; every other path gets ``index.html`` so the
    client-side router can handle it. Unknown API paths still get the JSON 404.
    Must be called after the API routers are included (the catch-all route comes last).
    """
    dist_dir = dist_dir.resolve()
    index = dist_dir / "index.html"
    if not index.is_file():
        raise RuntimeError(
            f"Frontend build not found at {dist_dir}. Run `npm run build` in frontend/."
        )
    if (dist_dir / "assets").is_dir():
        # Hashed file names, so they can be cached for good.
        app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")
    api = api_prefix.strip("/")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path == api or path.startswith(f"{api}/"):
            raise NotFoundError(f"No API route for /{path}.")
        file = (dist_dir / path).resolve()
        if path and file.is_file() and file.is_relative_to(dist_dir):
            return FileResponse(file)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
