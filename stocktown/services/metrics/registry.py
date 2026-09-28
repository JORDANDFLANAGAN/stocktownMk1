from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Final

from stocktown.services.metrics.base import Metric, MetricValues
from stocktown.services.metrics.beta import Beta1y
from stocktown.services.metrics.day_change import DayChange
from stocktown.services.metrics.market_data import MarketData
from stocktown.services.metrics.max_drawdown import MaxDrawdown1y
from stocktown.services.metrics.off_high import OffFiftyTwoWeekHigh
from stocktown.services.metrics.one_year_return import OneYearReturn
from stocktown.services.metrics.relative_volume import RelativeVolume
from stocktown.services.metrics.volatility import Volatility30d

REQUIRED_METRIC_ATTRIBUTES: Final[tuple[str, ...]] = ("key", "label", "unit", "scale", "refresh")

# Display order for the frontend dropdown. Adding a metric = one class + one line here.
ALL_METRICS: Final[tuple[Metric, ...]] = (
    OneYearReturn(),
    DayChange(),
    Volatility30d(),
    MaxDrawdown1y(),
    OffFiftyTwoWeekHigh(),
    Beta1y(),
    RelativeVolume(),
)

def index_by_key(metrics: Iterable[Metric]) -> Mapping[str, Metric]:
    """Read-only key → metric map. Raises on missing metadata or duplicate keys."""
    metrics_by_key: dict[str, Metric] = {}
    for metric in metrics:
        missing = [name for name in REQUIRED_METRIC_ATTRIBUTES if not hasattr(metric, name)]
        if missing:
            raise TypeError(f"{type(metric).__name__} is missing {', '.join(missing)}")
        if metric.key in metrics_by_key:
            raise ValueError(f"Duplicate metric key {metric.key!r}")
        metrics_by_key[metric.key] = metric
    return MappingProxyType(metrics_by_key)


METRICS_BY_KEY: Final[Mapping[str, Metric]] = index_by_key(ALL_METRICS)


def get_metric(key: str) -> Metric:
    try:
        return METRICS_BY_KEY[key]
    except KeyError:
        available = ", ".join(METRICS_BY_KEY)
        raise KeyError(f"Unknown metric {key!r}. Available: {available}") from None


def compute_metrics(
    data: MarketData, *, metrics: tuple[Metric, ...] = ALL_METRICS
) -> dict[str, MetricValues]:
    """Values keyed by metric key, then ticker. All metrics share data's single fetch."""
    return {metric.key: metric.compute(data) for metric in metrics}
