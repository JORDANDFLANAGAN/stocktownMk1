from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator, Final

from websockets.asyncio.client import ClientConnection, connect

from stocktown.config import get_settings
from stocktown.domain.models import MinuteBar

ALPACA_STREAM_IEX_URL: Final[str] = "wss://stream.data.alpaca.markets/v2/iex"

BAR_MESSAGE_TYPE: Final[str] = "b"
SUCCESS_MESSAGE_TYPE: Final[str] = "success"
ERROR_MESSAGE_TYPE: Final[str] = "error"


class AlpacaBarConnection:
    """An authenticated Alpaca stream connection with bar subscriptions changeable at any time.

    subscribe/unsubscribe only send: bars() is the single reader of the socket, so
    subscription acknowledgements are consumed there rather than awaited here.
    """

    def __init__(self, socket: ClientConnection) -> None:
        self._socket = socket

    async def subscribe(self, tickers: list[str]) -> None:
        await self._socket.send(json.dumps({"action": "subscribe", "bars": tickers}))

    async def unsubscribe(self, tickers: list[str]) -> None:
        await self._socket.send(json.dumps({"action": "unsubscribe", "bars": tickers}))

    async def bars(self) -> AsyncIterator[MinuteBar]:
        """Yield minute bars until the connection closes; raise on any Alpaca error message."""
        async for raw_message in self._socket:
            for event in json.loads(raw_message):
                event_type = event.get("T")
                if event_type == ERROR_MESSAGE_TYPE:
                    raise RuntimeError(f"Alpaca WS error: {event.get('msg')}")
                if event_type == BAR_MESSAGE_TYPE:
                    yield parse_minute_bar(event)


@asynccontextmanager
async def open_bar_connection() -> AsyncIterator[AlpacaBarConnection]:
    """Connect and authenticate to Alpaca's IEX stream. Free tier: one connection per account."""

    credentials = get_settings().alpaca
    async with connect(ALPACA_STREAM_IEX_URL) as socket:
        await expect_message(
            socket, message_type=SUCCESS_MESSAGE_TYPE, message_body="connected"
        )
        await authenticate(
            socket, api_key=credentials.api_key, api_secret=credentials.api_secret
        )
        yield AlpacaBarConnection(socket)


async def stream_minute_bars(tickers: list[str]) -> AsyncIterator[MinuteBar]:
    """Yield minute bars for a fixed set of tickers (used by the CLI preview)."""

    async with open_bar_connection() as connection:
        await connection.subscribe(tickers)
        async for bar in connection.bars():
            yield bar


async def authenticate(
    socket: ClientConnection, *, api_key: str, api_secret: str
) -> None:
    await socket.send(
        json.dumps({"action": "auth", "key": api_key, "secret": api_secret})
    )
    await expect_message(
        socket, message_type=SUCCESS_MESSAGE_TYPE, message_body="authenticated"
    )


async def expect_message(
    socket: ClientConnection,
    *,
    message_type: str,
    message_body: str | None = None,
) -> dict[str, Any]:
    """Consume messages until one matching (type, body) arrives; raise on any error message."""

    while True:
        raw_message = await socket.recv()
        for event in json.loads(raw_message):
            event_type = event.get("T")
            if event_type == ERROR_MESSAGE_TYPE:
                raise RuntimeError(f"Alpaca WS error: {event.get('msg')}")
            if event_type == message_type and (
                message_body is None or event.get("msg") == message_body
            ):
                return event


def parse_minute_bar(event: dict[str, Any]) -> MinuteBar:
    return MinuteBar(
        ticker=str(event["S"]),
        minute_utc=parse_utc_datetime(event["t"]),
        open=float(event["o"]),
        high=float(event["h"]),
        low=float(event["l"]),
        close=float(event["c"]),
        volume=int(event["v"]),
    )


def parse_utc_datetime(iso_timestamp: str) -> datetime:
    return datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
