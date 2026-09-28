from datetime import date

import pytest

from stocktown.services.metrics.day_change import day_change
from tests.factories import AS_OF, make_series


def test_day_change_compares_the_latest_close_with_the_previous_close():
    bars = make_series([100.0, 105.0])

    assert day_change(bars, latest_session=AS_OF) == pytest.approx(0.05)


def test_a_halted_stock_does_not_report_an_old_move_as_todays_change():
    last_traded_tuesday = make_series([100.0, 105.0], last_day=date(2026, 9, 22))

    assert day_change(last_traded_tuesday, latest_session=AS_OF) is None
