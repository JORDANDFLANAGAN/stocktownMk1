"""Builders for hand-written price series, so each test states only the numbers it cares about."""

from __future__ import annotations

import random
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Final

from stocktown.domain.models import DailyBar

AS_OF: Final[date] = date(2026, 9, 25)  # a Friday
DEFAULT_VOLUME: Final[int] = 1_000

# ~13 months of irregular daily market moves (mean 0, ~1% stdev). Seeded, so every run is identical;
# irregular, so a series shifted by a few days no longer lines up with the original.
_seeded_rng = random.Random(42)
MARKET_RETURNS: Final[list[float]] = [_seeded_rng.gauss(0, 0.01) for _ in range(270)]


def make_bar(
    trading_date: date,
    close: float,
    *,
    high: float | None = None,
    volume: int = DEFAULT_VOLUME,
    ticker: str = "TEST",
) -> DailyBar:
    return DailyBar(
        ticker=ticker,
        trading_date=trading_date,
        open=close,
        high=close if high is None else high,
        low=close,
        close=close,
        volume=volume,
    )


def make_series(
    closes: Sequence[float],
    *,
    last_day: date = AS_OF,
    volumes: Sequence[int] | None = None,
    ticker: str = "TEST",
) -> list[DailyBar]:
    """One bar per consecutive weekday, ending on last_day, oldest first."""
    days = weekdays_ending(last_day, count=len(closes))
    volumes = volumes if volumes is not None else [DEFAULT_VOLUME] * len(closes)
    return [
        make_bar(day, close, volume=volume, ticker=ticker)
        for day, close, volume in zip(days, closes, volumes, strict=True)
    ]


def year_of_bars_loader(
    tickers: list[str], *, start: date, end: date
) -> dict[str, list[DailyBar]]:
    """Fake Alpaca loader: 13 months of irregular prices for every requested ticker."""
    return {
        ticker: make_series(closes_from_returns(MARKET_RETURNS), ticker=ticker)
        for ticker in tickers
    }


class FakeClock:
    """Stands in for date.today, so tests can move to the next day."""

    def __init__(self, today: date = AS_OF) -> None:
        self.today = today

    def __call__(self) -> date:
        return self.today

    def advance_one_day(self) -> None:
        self.today += timedelta(days=1)


def closes_from_returns(daily_returns: Sequence[float], *, start: float = 100.0) -> list[float]:
    closes = [start]
    for daily_return in daily_returns:
        closes.append(closes[-1] * (1 + daily_return))
    return closes


def weekdays_ending(last_day: date, *, count: int) -> list[date]:
    days: list[date] = []
    day = last_day
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day -= timedelta(days=1)
    return days[::-1]
