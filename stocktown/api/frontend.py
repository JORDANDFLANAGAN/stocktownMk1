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
# Never pages: an unknown path under these is a real 404, not the app. (A missing old JS file
# after a deploy must fail as a 404, not come back as HTML.)
NOT_PAGE_PREFIXES: Final[tuple[str, ...]] = ("api/", "assets/")
# Revalidate the entry page on every visit (a cheap 304 via its ETag), so a deploy's newly named
# assets are picked up straight away.
ENTRY_CACHE_CONTROL: Final[str] = "no-cache"


class SinglePageApp(StaticFiles):
    """Serves the built files; any other page path gets index.html so the Vue router can
    resolve deep links like /spy/town/ticker/AAPL. Unknown /api and /assets paths stay a 404."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or path.startswith(NOT_PAGE_PREFIXES):
                raise
            entry_page = await super().get_response(SPA_ENTRY_FILE, scope)
            entry_page.headers["Cache-Control"] = ENTRY_CACHE_CONTROL
            return entry_page
