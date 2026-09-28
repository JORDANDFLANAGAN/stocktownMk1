from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from stocktown.domain.models import DailyBar
from stocktown.services.metrics.base import Metric, MetricValues, Refresh, Scale, Unit
from stocktown.services.metrics.market_data import MarketData
from stocktown.services.metrics.price_series import (
    bars_since,
    has_history_since,
    one_year_before,
)


class OffFiftyTwoWeekHigh(Metric):
    key = "off_52_week_high"
    label = "Off 52-week high"
    unit = Unit.PERCENT
    scale = Scale.PERCENTILE
    refresh = Refresh.DAILY

    def compute(self, data: MarketData) -> MetricValues:
        start_date = one_year_before(data.as_of)
        return {
            ticker: off_52_week_high(data.daily_bars.get(ticker, []), start_date=start_date)
            for ticker in data.tickers
        }


def off_52_week_high(bars: Sequence[DailyBar], *, start_date: date) -> float | None:
    """Latest close relative to the 52-week high (0 = at the high, -0.2 = 20% below).

    Uses intraday highs, the usual 52-week-high convention, so a stock that closes at its
    peak can still read slightly below 0.
    """
    if not has_history_since(bars, start_date):
        return None
    window = bars_since(bars, start_date)
    return window[-1].close / max(bar.high for bar in window) - 1
