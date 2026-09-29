from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from typing import Any, Final, Iterator

import httpx

from stocktown.domain.models import DailyBar, MinuteBar
from stocktown.providers.alpaca.client import ALPACA_DATA_BASE_URL, build_client

HISTORICAL_BARS_ENDPOINT: Final[str] = "/v2/stocks/bars"
LATEST_BARS_ENDPOINT: Final[str] = "/v2/stocks/bars/latest"

# Free tier: IEX feed only. Split-adjusted so 1-year returns stay accurate across splits.
FREE_TIER_FEED: Final[str] = "iex"
SPLIT_ADJUSTED: Final[str] = "split"
DAILY_TIMEFRAME: Final[str] = "1Day"

MAX_SYMBOLS_PER_REQUEST: Final[int] = 100
MAX_BARS_PER_PAGE: Final[int] = 10_000
# Batches are fetched side by side: one after another, a full S&P 500 build is ~15 requests of
# ~1.5s each. The request count is unchanged (far below the free tier's 200/minute); 4 in flight
# keeps bursts gentle.
MAX_CONCURRENT_BATCHES: Final[int] = 4


def load_daily_bars(
    tickers: list[str], *, start: date, end: date
) -> dict[str, list[DailyBar]]:
    """Fetch split-adjusted daily bars for each ticker between start and end (inclusive)."""

    batches = list(chunk_symbols(tickers, MAX_SYMBOLS_PER_REQUEST))
    bars_by_ticker: dict[str, list[DailyBar]] = {}

    # httpx.Client is safe to share across threads (one connection pool).
    with (
        build_client(ALPACA_DATA_BASE_URL) as client,
        ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BATCHES) as pool,
    ):
        batch_results = pool.map(
            lambda batch: fetch_bars_for_batch(client, symbols=batch, start=start, end=end),
            batches,
        )
        for batch_result in batch_results:
            for ticker, bars in batch_result.items():
                bars_by_ticker.setdefault(ticker, []).extend(bars)

    return bars_by_ticker


def load_latest_bar(ticker: str) -> MinuteBar | None:
    """Most recent minute bar — the last close when the market is shut. None if Alpaca has none."""

    with build_client(ALPACA_DATA_BASE_URL) as client:
        response = client.get(
            LATEST_BARS_ENDPOINT, params={"symbols": ticker, "feed": FREE_TIER_FEED}
        )
        response.raise_for_status()
    raw_bar = response.json().get("bars", {}).get(ticker)
    return None if raw_bar is None else parse_minute_bar(ticker, raw_bar)


def chunk_symbols(symbols: list[str], batch_size: int) -> Iterator[list[str]]:
    for start_index in range(0, len(symbols), batch_size):
        yield symbols[start_index : start_index + batch_size]


def fetch_bars_for_batch(
    client: httpx.Client,
    *,
    symbols: list[str],
    start: date,
    end: date,
) -> dict[str, list[DailyBar]]:
    bars_by_ticker: dict[str, list[DailyBar]] = {}
    page_token: str | None = None

    while True:
        page = fetch_bars_page(
            client, symbols=symbols, start=start, end=end, page_token=page_token
        )
        for ticker, raw_bars in (page.get("bars") or {}).items():
            bars_by_ticker.setdefault(ticker, []).extend(
                parse_daily_bar(ticker, raw_bar) for raw_bar in raw_bars
            )

        page_token = page.get("next_page_token")
        if not page_token:
            return bars_by_ticker


def fetch_bars_page(
    client: httpx.Client,
    *,
    symbols: list[str],
    start: date,
    end: date,
    page_token: str | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "symbols": ",".join(symbols),
        "timeframe": DAILY_TIMEFRAME,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "adjustment": SPLIT_ADJUSTED,
        "feed": FREE_TIER_FEED,
        "limit": MAX_BARS_PER_PAGE,
    }
    if page_token:
        params["page_token"] = page_token

    response = client.get(HISTORICAL_BARS_ENDPOINT, params=params)
    response.raise_for_status()
    return response.json()


def parse_daily_bar(ticker: str, raw_bar: dict[str, Any]) -> DailyBar:
    return DailyBar(
        ticker=ticker,
        trading_date=parse_trading_date(raw_bar["t"]),
        open=float(raw_bar["o"]),
        high=float(raw_bar["h"]),
        low=float(raw_bar["l"]),
        close=float(raw_bar["c"]),
        volume=int(raw_bar["v"]),
    )


def parse_minute_bar(ticker: str, raw_bar: dict[str, Any]) -> MinuteBar:
    return MinuteBar(
        ticker=ticker,
        minute_utc=datetime.fromisoformat(raw_bar["t"].replace("Z", "+00:00")),
        open=float(raw_bar["o"]),
        high=float(raw_bar["h"]),
        low=float(raw_bar["l"]),
        close=float(raw_bar["c"]),
        volume=int(raw_bar["v"]),
    )


def parse_trading_date(iso_timestamp: str) -> date:
    return datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00")).date()
