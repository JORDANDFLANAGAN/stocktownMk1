from datetime import date

import pytest

from stocktown.services.metrics.relative_volume import relative_volume
from tests.factories import AS_OF, make_series

TWENTY_ONE_CLOSES = [100.0] * 21


def test_relative_volume_compares_the_latest_day_with_the_previous_20_day_average():
    # If the latest day leaked into its own average, this would read ~2.73 instead of 3.
    bars = make_series(TWENTY_ONE_CLOSES, volumes=[1_000] * 20 + [3_000])

    assert relative_volume(bars, latest_session=AS_OF) == pytest.approx(3.0)


def test_no_prior_volume_gives_no_value_instead_of_dividing_by_zero():
    bars = make_series(TWENTY_ONE_CLOSES, volumes=[0] * 20 + [500])

    assert relative_volume(bars, latest_session=AS_OF) is None


def test_a_halted_stock_does_not_report_an_old_session_as_todays_volume():
    last_traded_tuesday = make_series(
        TWENTY_ONE_CLOSES, volumes=[1_000] * 20 + [3_000], last_day=date(2026, 9, 22)
    )

    assert relative_volume(last_traded_tuesday, latest_session=AS_OF) is None
