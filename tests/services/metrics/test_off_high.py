from datetime import date

import pytest

from stocktown.services.metrics.off_high import off_52_week_high
from tests.factories import AS_OF, make_bar

ONE_YEAR_AGO = date(2025, 9, 25)


def test_distance_is_measured_from_the_intraday_high_not_the_highest_close():
    bars = [
        make_bar(ONE_YEAR_AGO, 100.0),
        make_bar(date(2026, 5, 1), 180.0, high=200.0),
        make_bar(AS_OF, 150.0),
    ]

    assert off_52_week_high(bars, start_date=ONE_YEAR_AGO) == pytest.approx(-0.25)


def test_highs_from_before_the_52_week_window_are_ignored():
    bars = [
        make_bar(date(2025, 8, 1), 500.0, high=500.0),  # outside the window
        make_bar(ONE_YEAR_AGO, 100.0),
        make_bar(AS_OF, 150.0),
    ]

    assert off_52_week_high(bars, start_date=ONE_YEAR_AGO) == pytest.approx(0.0)
