from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from stocktown.domain.models import DailyBar
from stocktown.services.metrics.base import Metric, MetricValues, Refresh, Scale, Unit
from stocktown.services.metrics.market_data import MarketData
from stocktown.services.metrics.price_series import (
    bars_since,
    closing_prices,
    has_history_since,
    one_year_before,
)


class MaxDrawdown1y(Metric):
    key = "max_drawdown_1y"
    label = "Max drawdown (1-year)"
    unit = Unit.PERCENT
    scale = Scale.PERCENTILE
    refresh = Refresh.DAILY

    def compute(self, data: MarketData) -> MetricValues:
        start_date = one_year_before(data.as_of)
        return {
            ticker: max_drawdown(data.daily_bars.get(ticker, []), start_date=start_date)
            for ticker in data.tickers
        }


def max_drawdown(bars: Sequence[DailyBar], *, start_date: date) -> float | None:
    """Worst peak-to-trough fall in closing price, as a negative fraction (-0.35 = 35% drop)."""
    if not has_history_since(bars, start_date):
        return None
    running_peak = 0.0
    worst_drawdown = 0.0
    for close in closing_prices(bars_since(bars, start_date)):
        running_peak = max(running_peak, close)
        worst_drawdown = min(worst_drawdown, close / running_peak - 1)
    return worst_drawdown
