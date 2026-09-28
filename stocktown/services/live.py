from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Final, Literal, Protocol

from stocktown.domain.models import MinuteBar
from stocktown.providers.alpaca.stream import open_bar_connection

VIEWER_QUEUE_SIZE: Final[int] = 10
IDLE_DISCONNECT_SECONDS: Final[float] = 60.0
INITIAL_RECONNECT_DELAY_SECONDS: Final[float] = 1.0
MAX_RECONNECT_DELAY_SECONDS: Final[float] = 30.0

logger = logging.getLogger(__name__)


class BarConnection(Protocol):
    async def subscribe(self, tickers: list[str]) -> None: ...
    async def unsubscribe(self, tickers: list[str]) -> None: ...
    def bars(self) -> AsyncIterator[MinuteBar]: ...


UpstreamConnector = Callable[[], AbstractAsyncContextManager[BarConnection]]
ViewerQueue = asyncio.Queue[MinuteBar]


class LiveBarHub:
    """Shares Alpaca's single WebSocket connection between every open popup.

    The first viewer of a ticker subscribes it upstream and the last to leave unsubscribes it.
    The connection opens with the first viewer, closes after a quiet period with no viewers,
    and reconnects (re-subscribing every watched ticker) if it drops.
    """

    def __init__(
        self,
        *,
        connect_upstream: UpstreamConnector = open_bar_connection,
        idle_disconnect_seconds: float = IDLE_DISCONNECT_SECONDS,
        initial_reconnect_delay_seconds: float = INITIAL_RECONNECT_DELAY_SECONDS,
        queue_size: int = VIEWER_QUEUE_SIZE,
    ) -> None:
        self._connect_upstream = connect_upstream
        self._idle_disconnect_seconds = idle_disconnect_seconds
        self._initial_reconnect_delay_seconds = initial_reconnect_delay_seconds
        self._queue_size = queue_size
        self._viewers_by_ticker: dict[str, set[ViewerQueue]] = {}
        self._connection: BarConnection | None = None
        self._upstream_task: asyncio.Task[None] | None = None
        self._idle_timer: asyncio.Task[None] | None = None

    @asynccontextmanager
    async def watch(self, ticker: str) -> AsyncIterator[ViewerQueue]:
        """Receive live bars for ticker until the block exits."""
        queue: ViewerQueue = asyncio.Queue(maxsize=self._queue_size)
        await self._add_viewer(ticker, queue)
        try:
            yield queue
        finally:
            await self._remove_viewer(ticker, queue)

    async def close(self) -> None:
        """Stop the upstream connection (app shutdown)."""
        for task in (self._idle_timer, self._upstream_task):
            if task is not None:
                task.cancel()
        self._idle_timer = None
        self._upstream_task = None

    async def _add_viewer(self, ticker: str, queue: ViewerQueue) -> None:
        self._cancel_idle_timer()
        is_first_viewer = ticker not in self._viewers_by_ticker
        self._viewers_by_ticker.setdefault(ticker, set()).add(queue)
        if is_first_viewer:
            await self._send_upstream("subscribe", ticker)
        self._ensure_upstream_running()

    async def _remove_viewer(self, ticker: str, queue: ViewerQueue) -> None:
        viewers = self._viewers_by_ticker.get(ticker, set())
        viewers.discard(queue)
        if viewers:
            return
        self._viewers_by_ticker.pop(ticker, None)
        await self._send_upstream("unsubscribe", ticker)
        if not self._viewers_by_ticker:
            self._idle_timer = asyncio.create_task(self._disconnect_when_idle())

    async def _send_upstream(
        self, action: Literal["subscribe", "unsubscribe"], ticker: str
    ) -> None:
        """Best effort: if the connection is down, the reconnect re-subscribes from scratch."""
        connection = self._connection
        if connection is None:
            return
        try:
            if action == "subscribe":
                await connection.subscribe([ticker])
            else:
                await connection.unsubscribe([ticker])
        except Exception:
            logger.warning("Could not %s %s upstream; the reconnect will resync", action, ticker)

    def _ensure_upstream_running(self) -> None:
        if self._upstream_task is None or self._upstream_task.done():
            self._upstream_task = asyncio.create_task(self._run_upstream())

    async def _run_upstream(self) -> None:
        reconnect_delay = self._initial_reconnect_delay_seconds
        while True:
            try:
                async with self._connect_upstream() as connection:
                    self._connection = connection
                    reconnect_delay = self._initial_reconnect_delay_seconds
                    if self._viewers_by_ticker:
                        await connection.subscribe(sorted(self._viewers_by_ticker))
                    async for bar in connection.bars():
                        self._deliver(bar)
            except Exception:
                logger.exception("Live bar connection dropped; reconnecting in %.0fs", reconnect_delay)
            finally:
                self._connection = None
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY_SECONDS)

    def _deliver(self, bar: MinuteBar) -> None:
        for queue in self._viewers_by_ticker.get(bar.ticker, ()):
            if queue.full():
                queue.get_nowait()  # drop the oldest: a popup only needs the latest price
            queue.put_nowait(bar)

    async def _disconnect_when_idle(self) -> None:
        await asyncio.sleep(self._idle_disconnect_seconds)
        if not self._viewers_by_ticker and self._upstream_task is not None:
            self._upstream_task.cancel()
            self._upstream_task = None

    def _cancel_idle_timer(self) -> None:
        if self._idle_timer is not None:
            self._idle_timer.cancel()
            self._idle_timer = None
