from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from typing import Final

from stocktown.domain.models import DailyBar
from stocktown.services.metrics.base import Metric, MetricValues, Refresh, Scale, Unit
from stocktown.services.metrics.market_data import MarketData
from stocktown.services.metrics.price_series import (
    TRADING_DAYS_PER_YEAR,
    closing_prices,
    log_returns,
)

VOLATILITY_WINDOW_DAYS: Final[int] = 30


class Volatility30d(Metric):
    key = "volatility_30d"
    label = "Volatility (30-day)"
    unit = Unit.PERCENT
    scale = Scale.PERCENTILE
    refresh = Refresh.DAILY

    def compute(self, data: MarketData) -> MetricValues:
        return {
            ticker: annualised_volatility(data.daily_bars.get(ticker, []))
            for ticker in data.tickers
        }


def annualised_volatility(
    bars: Sequence[DailyBar], *, window_days: int = VOLATILITY_WINDOW_DAYS
) -> float | None:
    """Annualised standard deviation of daily log returns over the last window_days."""
    if len(bars) < window_days + 1:
        return None
    returns = log_returns(closing_prices(bars[-(window_days + 1):]))
    return statistics.stdev(returns) * math.sqrt(TRADING_DAYS_PER_YEAR)
