from datetime import date

import pytest

from stocktown.services.metrics.one_year_return import one_year_return
from tests.factories import AS_OF, make_bar

ONE_YEAR_AGO = date(2025, 9, 25)


def test_return_is_measured_from_the_close_one_year_ago_not_the_oldest_bar_fetched():
    bars = [
        make_bar(date(2025, 8, 1), 50.0),  # fetched as a buffer; must not be the baseline
        make_bar(ONE_YEAR_AGO, 100.0),
        make_bar(AS_OF, 120.0),
    ]

    assert one_year_return(bars, start_date=ONE_YEAR_AGO) == pytest.approx(0.20)


def test_when_one_year_ago_was_not_a_trading_day_the_previous_close_is_the_baseline():
    saturday = date(2025, 9, 27)
    bars = [
        make_bar(date(2025, 9, 26), 100.0),  # Friday before
        make_bar(date(2025, 9, 29), 90.0),  # Monday after
        make_bar(AS_OF, 120.0),
    ]

    assert one_year_return(bars, start_date=saturday) == pytest.approx(0.20)


def test_a_stock_listed_less_than_a_year_ago_has_no_one_year_return():
    bars = [make_bar(date(2026, 1, 5), 100.0), make_bar(AS_OF, 150.0)]

    assert one_year_return(bars, start_date=ONE_YEAR_AGO) is None
