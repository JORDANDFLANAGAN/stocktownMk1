import math

import pytest

from stocktown.services.metrics.volatility import annualised_volatility
from tests.factories import make_series

# Closes alternating 100 → 110 → 100 give daily log returns of exactly ±ln(1.1).
ALTERNATING_CLOSES = [100.0 if day % 2 == 0 else 110.0 for day in range(31)]
DAILY_LOG_MOVE = math.log(1.1)
# Sample stdev of 30 returns alternating ±a is a·√(30/29); annualised over 252 trading days.
EXPECTED_ANNUALISED_VOLATILITY = DAILY_LOG_MOVE * math.sqrt(30 / 29) * math.sqrt(252)


def test_volatility_is_the_annualised_standard_deviation_of_daily_log_returns():
    bars = make_series(ALTERNATING_CLOSES)

    assert annualised_volatility(bars) == pytest.approx(EXPECTED_ANNUALISED_VOLATILITY)


def test_turbulence_older_than_the_30_day_window_does_not_affect_volatility():
    crash_then_calm = [100.0, 40.0, 180.0, 20.0, 100.0] + ALTERNATING_CLOSES

    assert annualised_volatility(make_series(crash_then_calm)) == pytest.approx(
        EXPECTED_ANNUALISED_VOLATILITY
    )


def test_fewer_than_30_daily_returns_gives_no_volatility():
    assert annualised_volatility(make_series(ALTERNATING_CLOSES[:30])) is None
