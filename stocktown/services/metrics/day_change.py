from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from stocktown.domain.models import DailyBar
from stocktown.services.metrics.base import Metric, MetricValues, Refresh, Scale, Unit
from stocktown.services.metrics.market_data import MarketData
from stocktown.services.metrics.price_series import is_current


class DayChange(Metric):
    key = "day_change"
    label = "Day change"
    unit = Unit.PERCENT
    # Linear keeps the sign meaningful for the red–grey–green diverging colour scale.
    scale = Scale.LINEAR
    refresh = Refresh.DAILY

    def compute(self, data: MarketData) -> MetricValues:
        return {
            ticker: day_change(data.daily_bars.get(ticker, []), latest_session=data.latest_session)
            for ticker in data.tickers
        }


def day_change(bars: Sequence[DailyBar], *, latest_session: date | None) -> float | None:
    if len(bars) < 2 or not is_current(bars, latest_session):
        return None
    return bars[-1].close / bars[-2].close - 1
