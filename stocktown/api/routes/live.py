from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Final

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool

from stocktown.api.dependencies import (
    LatestBarLoader,
    get_asset_catalogue,
    get_latest_bar_loader,
    get_live_bar_hub,
)
from stocktown.api.schemas import LiveBarMessage
from stocktown.exceptions import UnknownTickerError, UpstreamUnavailableError
from stocktown.services.assets import AssetCatalogue
from stocktown.services.live import LiveBarHub, ViewerQueue

# Application-defined close codes (RFC 6455 reserves 4000-4999 for apps), mirroring HTTP.
CLOSE_UNKNOWN_TICKER: Final[int] = 4404
CLOSE_UPSTREAM_UNAVAILABLE: Final[int] = 4503

logger = logging.getLogger(__name__)

router = APIRouter(tags=["live"])


@router.websocket("/live")
async def stream_live_bars(
    websocket: WebSocket,
    ticker: str,
    assets: Annotated[AssetCatalogue, Depends(get_asset_catalogue)],
    hub: Annotated[LiveBarHub, Depends(get_live_bar_hub)],
    load_latest_bar: Annotated[LatestBarLoader, Depends(get_latest_bar_loader)],
) -> None:
    """Popup price feed: the latest bar immediately, then each new minute bar as it arrives."""
    try:
        asset = await run_in_threadpool(assets.find, ticker)
    except UnknownTickerError as error:
        await refuse(websocket, code=CLOSE_UNKNOWN_TICKER, reason=str(error))
        return
    except UpstreamUnavailableError as error:
        await refuse(websocket, code=CLOSE_UPSTREAM_UNAVAILABLE, reason=str(error))
        return

    await websocket.accept()
    async with hub.watch(asset.symbol) as live_bars:
        await send_latest_bar(websocket, asset.symbol, load_latest_bar)
        await forward_until_disconnect(websocket, live_bars)


async def refuse(websocket: WebSocket, *, code: int, reason: str) -> None:
    """Accept first: close codes only reach the browser after the handshake. Closing before
    accept() is sent as a bare HTTP 403 the page can't tell apart from other failures."""
    await websocket.accept()
    await websocket.close(code=code, reason=reason)


async def send_latest_bar(
    websocket: WebSocket, symbol: str, load_latest_bar: LatestBarLoader
) -> None:
    """Best effort, so the popup isn't blank until the next minute; live bars follow regardless."""
    try:
        latest_bar = await run_in_threadpool(load_latest_bar, symbol)
    except Exception:
        logger.warning("Could not load the latest bar for %s", symbol)
        return
    if latest_bar is not None:
        await websocket.send_text(LiveBarMessage.from_bar(latest_bar).model_dump_json())


async def forward_until_disconnect(websocket: WebSocket, live_bars: ViewerQueue) -> None:
    """Send bars until the browser goes away — noticed even when no bars are flowing."""
    async with asyncio.TaskGroup() as tasks:
        sender = tasks.create_task(send_bars(websocket, live_bars))
        await wait_for_disconnect(websocket)
        sender.cancel()


async def send_bars(websocket: WebSocket, live_bars: ViewerQueue) -> None:
    while True:
        bar = await live_bars.get()
        await websocket.send_text(LiveBarMessage.from_bar(bar).model_dump_json())


async def wait_for_disconnect(websocket: WebSocket) -> None:
    """The popup never sends anything; we only listen for it closing."""
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
    except WebSocketDisconnect:
        return
