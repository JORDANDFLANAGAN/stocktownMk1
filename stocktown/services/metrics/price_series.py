from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date
from itertools import pairwise
from typing import Final

from stocktown.domain.models import DailyBar

TRADING_DAYS_PER_YEAR: Final[int] = 252
CALENDAR_DAYS_PER_YEAR: Final[int] = 365

# Assumes bars are sorted oldest-first, which Alpaca guarantees per symbol.


def closing_prices(bars: Sequence[DailyBar]) -> list[float]:
    return [bar.close for bar in bars]


def simple_returns(closes: Sequence[float]) -> list[float]:
    return [current / previous - 1 for previous, current in pairwise(closes)]


def log_returns(closes: Sequence[float]) -> list[float]:
    return [math.log(current / previous) for previous, current in pairwise(closes)]


def one_year_before(as_of: date) -> date:
    return date.fromordinal(as_of.toordinal() - CALENDAR_DAYS_PER_YEAR)


def has_history_since(bars: Sequence[DailyBar], start_date: date) -> bool:
    """True when the series starts on or before start_date (i.e. isn't a recent listing)."""
    return bool(bars) and bars[0].trading_date <= start_date


def is_current(bars: Sequence[DailyBar], latest_session: date | None) -> bool:
    """True when the last bar is from the latest session (not halted or delisted).

    An unknown latest_session (benchmark missing) is treated as current.
    """
    if not bars:
        return False
    return latest_session is None or bars[-1].trading_date >= latest_session


def bars_since(bars: Sequence[DailyBar], start_date: date) -> list[DailyBar]:
    """Bars from the last one on or before start_date through to the latest."""
    start_index = max(
        (index for index, bar in enumerate(bars) if bar.trading_date <= start_date),
        default=0,
    )
    return list(bars[start_index:])
