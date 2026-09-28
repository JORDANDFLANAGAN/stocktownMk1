import pytest

from stocktown.services.metrics.beta import beta
from stocktown.services.metrics.price_series import one_year_before
from tests.factories import AS_OF, MARKET_RETURNS, closes_from_returns, make_series

ONE_YEAR_AGO = one_year_before(AS_OF)


def benchmark_bars():
    return make_series(closes_from_returns(MARKET_RETURNS), ticker="SPY")


def test_a_stock_that_moves_twice_as_much_as_the_market_has_a_beta_of_two():
    doubled = make_series(closes_from_returns([2 * r for r in MARKET_RETURNS]))

    assert beta(doubled, benchmark_bars(), start_date=ONE_YEAR_AGO) == pytest.approx(2.0)


def test_days_the_stock_did_not_trade_are_skipped_rather_than_misaligned():
    doubled = make_series(closes_from_returns([2 * r for r in MARKET_RETURNS]))
    halted_for_three_days = doubled[:150] + doubled[153:]

    # Returns across the gap compound slightly differently, so ~2 rather than exactly 2.
    # Misaligned dates would scramble the pairing and collapse beta towards 0.
    assert beta(halted_for_three_days, benchmark_bars(), start_date=ONE_YEAR_AGO) == pytest.approx(
        2.0, rel=0.05
    )
