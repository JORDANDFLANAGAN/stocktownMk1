from __future__ import annotations

from pathlib import Path
from typing import Final

from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

# The Vite build output, next to the backend package (same layout in the Docker image).
FRONTEND_DIST_DIR: Final[Path] = Path(__file__).resolve().parents[2] / "frontend" / "dist"
SPA_ENTRY_FILE: Final[str] = "index.html"
API_PATH_PREFIX: Final[str] = "api/"


class SinglePageApp(StaticFiles):
    """Serves the built files; any other page path gets index.html so the Vue router can
    resolve deep links like /spy/town/ticker/AAPL. Unknown /api paths stay a 404."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or path.startswith(API_PATH_PREFIX):
                raise
            return await super().get_response(SPA_ENTRY_FILE, scope)
