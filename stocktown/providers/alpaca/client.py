from __future__ import annotations

from typing import Final

import httpx

from stocktown.config import get_settings

ALPACA_DATA_BASE_URL: Final[str] = "https://data.alpaca.markets"
ALPACA_TRADING_BASE_URL: Final[str] = "https://paper-api.alpaca.markets"

DEFAULT_REQUEST_TIMEOUT_SECONDS: Final[float] = 30.0


def build_client(
    base_url: str, *, timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS
) -> httpx.Client:
    """Return an httpx.Client pre-configured with Alpaca auth headers for the given base URL."""

    credentials = get_settings().alpaca
    return httpx.Client(
        base_url=base_url,
        headers={
            "APCA-API-KEY-ID": credentials.api_key,
            "APCA-API-SECRET-KEY": credentials.api_secret,
        },
        timeout=timeout_seconds,
    )
