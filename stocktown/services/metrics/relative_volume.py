from __future__ import annotations

import statistics
from collections.abc import Sequence
from datetime import date
from typing import Final

from stocktown.domain.models import DailyBar
from stocktown.services.metrics.base import Metric, MetricValues, Refresh, Scale, Unit
from stocktown.services.metrics.market_data import MarketData
from stocktown.services.metrics.price_series import is_current

AVERAGE_VOLUME_WINDOW_DAYS: Final[int] = 20


class RelativeVolume(Metric):
    key = "relative_volume"
    label = "Relative volume (vs 20-day avg)"
    unit = Unit.RATIO
    scale = Scale.PERCENTILE
    refresh = Refresh.DAILY
    signed = False

    def compute(self, data: MarketData) -> MetricValues:
        return {
            ticker: relative_volume(
                data.daily_bars.get(ticker, []), latest_session=data.latest_session
            )
            for ticker in data.tickers
        }


def relative_volume(
    bars: Sequence[DailyBar],
    *,
    latest_session: date | None,
    window_days: int = AVERAGE_VOLUME_WINDOW_DAYS,
) -> float | None:
    """Latest session's volume vs the average of the preceding days.

    Ratio only — IEX volume is partial. Assumes the latest bar is a completed session.
    """
    if len(bars) < window_days + 1 or not is_current(bars, latest_session):
        return None
    average_volume = statistics.fmean(bar.volume for bar in bars[-(window_days + 1):-1])
    return bars[-1].volume / average_volume if average_volume > 0 else None
