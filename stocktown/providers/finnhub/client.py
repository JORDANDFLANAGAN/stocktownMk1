from __future__ import annotations

from typing import Final

import httpx

from stocktown.config import get_settings

FINNHUB_BASE_URL: Final[str] = "https://finnhub.io/api/v1"
DEFAULT_REQUEST_TIMEOUT_SECONDS: Final[float] = 30.0


def build_client() -> httpx.Client:
    """Return an httpx.Client pre-configured with the Finnhub auth header."""
    credentials = get_settings().finnhub
    return httpx.Client(
        base_url=FINNHUB_BASE_URL,
        headers={"X-Finnhub-Token": credentials.api_key},
        timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS,
    )
