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


class OneYearReturn(Metric):
    key = "one_year_return"
    label = "1-year return"
    unit = Unit.PERCENT
    scale = Scale.PERCENTILE
    refresh = Refresh.DAILY
    signed = True

    def compute(self, data: MarketData) -> MetricValues:
        start_date = one_year_before(data.as_of)
        return {
            ticker: one_year_return(data.daily_bars.get(ticker, []), start_date=start_date)
            for ticker in data.tickers
        }


def one_year_return(bars: Sequence[DailyBar], *, start_date: date) -> float | None:
    if not has_history_since(bars, start_date):
        return None
    window = bars_since(bars, start_date)
    return window[-1].close / window[0].close - 1
