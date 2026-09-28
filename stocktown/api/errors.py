from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from stocktown.exceptions import UnknownTickerError, UnknownUniverseError, UpstreamUnavailableError


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(UnknownUniverseError, respond_not_found)
    app.add_exception_handler(UnknownTickerError, respond_not_found)
    app.add_exception_handler(UpstreamUnavailableError, respond_upstream_unavailable)


async def respond_not_found(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})


async def respond_upstream_unavailable(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, UpstreamUnavailableError)
    headers = (
        {"Retry-After": str(error.retry_after_seconds)}
        if error.retry_after_seconds is not None
        else {}
    )
    return JSONResponse(status_code=503, content={"detail": str(error)}, headers=headers)
