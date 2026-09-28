from datetime import date

import pytest

from stocktown.services.metrics.max_drawdown import max_drawdown
from tests.factories import AS_OF, make_bar

ONE_YEAR_AGO = date(2025, 9, 25)


def test_drawdown_is_the_worst_peak_to_trough_fall_even_after_a_full_recovery():
    bars = [
        make_bar(ONE_YEAR_AGO, 100.0),
        make_bar(date(2026, 1, 5), 150.0),  # peak
        make_bar(date(2026, 3, 2), 90.0),  # trough: -40% from peak
        make_bar(AS_OF, 200.0),  # new high
    ]

    assert max_drawdown(bars, start_date=ONE_YEAR_AGO) == pytest.approx(-0.40)


def test_a_fall_from_a_peak_older_than_one_year_is_ignored():
    bars = [
        make_bar(date(2025, 8, 1), 300.0),  # outside the window
        make_bar(ONE_YEAR_AGO, 100.0),
        make_bar(date(2026, 3, 2), 120.0),
        make_bar(AS_OF, 110.0),
    ]

    assert max_drawdown(bars, start_date=ONE_YEAR_AGO) == pytest.approx(110 / 120 - 1)
