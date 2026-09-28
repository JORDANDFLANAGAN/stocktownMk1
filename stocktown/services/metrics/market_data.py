from __future__ import annotations

from datetime import date, timedelta
from functools import cached_property
from typing import Final, Protocol

from stocktown.domain.models import DailyBar
from stocktown.providers.alpaca import load_daily_bars

# One year of history plus a buffer so a close from ~1 year ago exists despite weekends/holidays.
PRICE_HISTORY_DAYS: Final[int] = 400

# Fetched alongside every universe so relative metrics (e.g. beta) need no extra request.
BENCHMARK_TICKER: Final[str] = "SPY"


class DailyBarsLoader(Protocol):
    def __call__(
        self, tickers: list[str], *, start: date, end: date
    ) -> dict[str, list[DailyBar]]: ...


class MarketData:
    """Per-run provider data shared by all metrics, loaded lazily.

    Each source is fetched on first access and reused afterwards, so metrics sharing a
    source (e.g. 1yr return and volatility) trigger a single fetch.

    as_of should be a completed session: during US market hours today's bar is partial,
    which understates volume-based metrics. The daily snapshot is meant to run pre-market.
    """

    def __init__(
        self,
        tickers: list[str],
        *,
        as_of: date,
        bars_loader: DailyBarsLoader = load_daily_bars,
    ) -> None:
        self.tickers: tuple[str, ...] = tuple(tickers)
        self.as_of = as_of
        self._bars_loader = bars_loader

    @cached_property
    def daily_bars(self) -> dict[str, list[DailyBar]]:
        """Bars for every ticker plus the benchmark, fetched in one pass."""
        symbols = sorted(set(self.tickers) | {BENCHMARK_TICKER})
        start = self.as_of - timedelta(days=PRICE_HISTORY_DAYS)
        return self._bars_loader(symbols, start=start, end=self.as_of)

    @property
    def benchmark_bars(self) -> list[DailyBar]:
        return self.daily_bars.get(BENCHMARK_TICKER, [])

    @property
    def latest_session(self) -> date | None:
        """Most recent trading day, taken from the benchmark (it trades every session)."""
        benchmark_bars = self.benchmark_bars
        return benchmark_bars[-1].trading_date if benchmark_bars else None
