from __future__ import annotations

import statistics
from collections.abc import Sequence
from datetime import date
from typing import Final

from stocktown.domain.models import DailyBar
from stocktown.services.metrics.base import Metric, MetricValues, Refresh, Scale, Unit
from stocktown.services.metrics.market_data import MarketData
from stocktown.services.metrics.price_series import (
    bars_since,
    has_history_since,
    one_year_before,
    simple_returns,
)

# Roughly 80% of a trading year; fewer shared days makes the estimate unreliable.
MIN_ALIGNED_RETURNS: Final[int] = 200


class Beta1y(Metric):
    key = "beta_1y"
    label = "Beta vs S&P 500 (1-year)"
    unit = Unit.RATIO
    scale = Scale.LINEAR
    refresh = Refresh.DAILY

    def compute(self, data: MarketData) -> MetricValues:
        start_date = one_year_before(data.as_of)
        return {
            ticker: beta(
                data.daily_bars.get(ticker, []),
                data.benchmark_bars,
                start_date=start_date,
            )
            for ticker in data.tickers
        }


def beta(
    bars: Sequence[DailyBar],
    benchmark_bars: Sequence[DailyBar],
    *,
    start_date: date,
) -> float | None:
    """Covariance with the benchmark over its variance, on days both traded."""
    if not has_history_since(bars, start_date):
        return None
    stock_closes = {bar.trading_date: bar.close for bar in bars_since(bars, start_date)}
    benchmark_closes = {bar.trading_date: bar.close for bar in benchmark_bars}
    shared_dates = sorted(stock_closes.keys() & benchmark_closes.keys())

    stock_returns = simple_returns([stock_closes[day] for day in shared_dates])
    benchmark_returns = simple_returns([benchmark_closes[day] for day in shared_dates])
    if len(stock_returns) < MIN_ALIGNED_RETURNS:
        return None
    return statistics.covariance(stock_returns, benchmark_returns) / statistics.variance(
        benchmark_returns
    )
