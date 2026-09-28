"""Contracts every metric must honour, and the registry's fail-fast checks."""

from datetime import date

import pytest

from stocktown.domain.models import DailyBar
from stocktown.services.metrics import (
    ALL_METRICS,
    MarketData,
    Metric,
    MetricValues,
    Refresh,
    Scale,
    Unit,
    compute_metrics,
)
from stocktown.services.metrics.day_change import DayChange
from stocktown.services.metrics.registry import index_by_key
from tests.factories import AS_OF, MARKET_RETURNS, closes_from_returns, make_series

VARYING_VOLUMES = [1_000 + 10 * (day % 7) for day in range(len(MARKET_RETURNS) + 1)]


def realistic_bars_loader(
    tickers: list[str], *, start: date, end: date
) -> dict[str, list[DailyBar]]:
    """A year+ of varied bars for every ticker except UNKNOWN, which the provider doesn't know."""
    return {
        ticker: make_series(
            closes_from_returns(MARKET_RETURNS), volumes=VARYING_VOLUMES, ticker=ticker
        )
        for ticker in tickers
        if ticker != "UNKNOWN"
    }


@pytest.mark.parametrize("metric", ALL_METRICS, ids=lambda metric: metric.key)
def test_every_metric_returns_an_entry_for_every_requested_ticker(metric: Metric):
    data = MarketData(["AAPL", "UNKNOWN"], as_of=AS_OF, bars_loader=realistic_bars_loader)

    values = metric.compute(data)

    assert values.keys() == {"AAPL", "UNKNOWN"}
    assert values["AAPL"] is not None
    assert values["UNKNOWN"] is None


def test_all_metrics_share_one_price_fetch_that_includes_the_benchmark():
    fetched_ticker_lists: list[list[str]] = []

    def recording_loader(tickers, *, start, end):
        fetched_ticker_lists.append(list(tickers))
        return realistic_bars_loader(tickers, start=start, end=end)

    compute_metrics(MarketData(["AAPL", "MSFT"], as_of=AS_OF, bars_loader=recording_loader))

    assert fetched_ticker_lists == [["AAPL", "MSFT", "SPY"]]


def test_two_metrics_with_the_same_key_are_rejected_at_startup():
    with pytest.raises(ValueError, match="day_change"):
        index_by_key([DayChange(), DayChange()])


def test_a_metric_missing_display_metadata_is_rejected_at_startup():
    class Unlabelled(Metric):
        key = "unlabelled"
        unit = Unit.PERCENT
        scale = Scale.LINEAR
        refresh = Refresh.DAILY

        def compute(self, data: MarketData) -> MetricValues:
            return {}

    with pytest.raises(TypeError, match="label"):
        index_by_key([Unlabelled()])
