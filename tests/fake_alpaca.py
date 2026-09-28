"""An in-memory stand-in for Alpaca's bar stream, shared by hub and route tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import anyio
from anyio.abc import ObjectReceiveStream, ObjectSendStream

from stocktown.domain.models import MinuteBar

_DROP_CONNECTION = object()


class FakeAlpaca:
    """Stands in for Alpaca's stream: records subscriptions; tests push bars or drop the line."""

    def __init__(self, *, scripted_bars: Sequence[MinuteBar] = ()) -> None:
        """scripted_bars are delivered on each new connection — for tests that can't push."""
        self.scripted_bars = list(scripted_bars)
        self.subscribed: set[str] = set()
        self.subscribe_requests: list[list[str]] = []
        self.connections_opened = 0
        self.open_connections = 0
        self._incoming: ObjectSendStream[object] | None = None

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[FakeConnection]:
        self.connections_opened += 1
        self.open_connections += 1
        send, receive = anyio.create_memory_object_stream(max_buffer_size=100)
        for bar in self.scripted_bars:
            send.send_nowait(bar)
        self._incoming = send
        try:
            yield FakeConnection(self, receive)
        finally:
            self.open_connections -= 1
            self.subscribed.clear()  # like Alpaca: a new connection starts with no subscriptions

    async def push(self, bar: MinuteBar) -> None:
        await self._incoming.send(bar)

    async def drop_connection(self) -> None:
        await self._incoming.send(_DROP_CONNECTION)


class FakeConnection:
    def __init__(self, alpaca: FakeAlpaca, incoming: ObjectReceiveStream[object]) -> None:
        self._alpaca = alpaca
        self._incoming = incoming

    async def subscribe(self, tickers: list[str]) -> None:
        self._alpaca.subscribe_requests.append(tickers)
        self._alpaca.subscribed.update(tickers)

    async def unsubscribe(self, tickers: list[str]) -> None:
        self._alpaca.subscribed.difference_update(tickers)

    async def bars(self) -> AsyncIterator[MinuteBar]:
        async for item in self._incoming:
            if item is _DROP_CONNECTION:
                raise ConnectionError("network blip")
            yield item


def minute_bar(ticker: str, *, close: float) -> MinuteBar:
    minute = datetime(2026, 9, 28, 14, 30, tzinfo=timezone.utc)
    return MinuteBar(ticker, minute, close, close, close, close, 100)
