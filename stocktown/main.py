from __future__ import annotations

import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from stocktown.api.dependencies import get_live_bar_hub, get_snapshot_service
from stocktown.api.errors import register_error_handlers
from stocktown.api.routes import instruments, live, metrics, universes
from stocktown.config import get_cors_allowed_origins

DEFAULT_UNIVERSE_ID: Final[str] = "spy"
API_PREFIX: Final[str] = "/api"
GZIP_MINIMUM_BYTES: Final[int] = 1_000

logger = logging.getLogger(__name__)


def create_app(*, warm_on_startup: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if warm_on_startup:
            # Build the default city in the background so the first visitor doesn't wait ~11s.
            threading.Thread(target=build_default_snapshot, daemon=True).start()
        yield
        await get_live_bar_hub().close()

    app = FastAPI(title="Market City API", lifespan=lifespan)
    app.add_middleware(GZipMiddleware, minimum_size=GZIP_MINIMUM_BYTES)
    app.add_middleware(
        CORSMiddleware, allow_origins=list(get_cors_allowed_origins()), allow_methods=["GET"]
    )
    register_error_handlers(app)
    for route_module in (universes, metrics, instruments, live):
        app.include_router(route_module.router, prefix=API_PREFIX)
    return app


def build_default_snapshot() -> None:
    try:
        get_snapshot_service().get(DEFAULT_UNIVERSE_ID)
    except Exception:
        # Startup must not crash on a provider blip; the first request retries the build.
        logger.exception("Snapshot warm-up failed")


app = create_app()
