from __future__ import annotations

import time
from typing import Any, Final

import httpx

from stocktown.config import get_settings
from stocktown.domain.models import Fundamentals

FINNHUB_BASE_URL: Final[str] = "https://finnhub.io/api/v1"
STOCK_METRIC_ENDPOINT: Final[str] = "/stock/metric"

# Free tier caps requests at 60/min. 1.1s spacing keeps us well below the limit under jitter.
SECONDS_BETWEEN_REQUESTS: Final[float] = 1.1

DEFAULT_REQUEST_TIMEOUT_SECONDS: Final[float] = 30.0

# Finnhub exposes several P/E variants; use the first numeric one present in the response.
PE_CANDIDATE_FIELDS: Final[tuple[str, ...]] = (
    "peBasicExclExtraTTM",
    "peInclExtraTTM",
    "peNormalizedAnnual",
)

MARKET_CAP_FIELD: Final[str] = "marketCapitalization"
DIVIDEND_YIELD_FIELD: Final[str] = "dividendYieldIndicatedAnnual"


def load_fundamentals(tickers: list[str]) -> dict[str, Fundamentals]:
    """Fetch fundamentals for each ticker, respecting Finnhub's free-tier rate limit."""

    fundamentals_by_ticker: dict[str, Fundamentals] = {}
    with build_client() as client:
        for ticker in tickers:
            fundamentals_by_ticker[ticker] = fetch_fundamentals(client, ticker=ticker)
            time.sleep(SECONDS_BETWEEN_REQUESTS)
    return fundamentals_by_ticker


def load_ticker_fundamentals(ticker: str) -> Fundamentals:
    """Fetch one ticker's fundamentals — for on-demand requests, so no rate-limit sleep."""
    with build_client() as client:
        return fetch_fundamentals(client, ticker=ticker)


def build_client() -> httpx.Client:
    credentials = get_settings().finnhub
    return httpx.Client(
        base_url=FINNHUB_BASE_URL,
        headers={"X-Finnhub-Token": credentials.api_key},
        timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS,
    )


def fetch_fundamentals(client: httpx.Client, *, ticker: str) -> Fundamentals:
    response = client.get(
        STOCK_METRIC_ENDPOINT,
        params={"symbol": ticker, "metric": "all"},
    )
    response.raise_for_status()
    metric_body = response.json().get("metric") or {}

    return Fundamentals(
        ticker=ticker,
        pe_ratio=extract_pe_ratio(metric_body),
        market_cap=extract_optional_float(metric_body, field=MARKET_CAP_FIELD),
        dividend_yield=extract_optional_float(metric_body, field=DIVIDEND_YIELD_FIELD),
    )


def extract_pe_ratio(metric_body: dict[str, Any]) -> float | None:
    for field in PE_CANDIDATE_FIELDS:
        value = metric_body.get(field)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def extract_optional_float(metric_body: dict[str, Any], *, field: str) -> float | None:
    value = metric_body.get(field)
    return float(value) if isinstance(value, (int, float)) else None
