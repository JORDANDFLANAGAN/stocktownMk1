from stocktown.domain.models import Holding
from stocktown.services.universes import build_universe

# Alpaca's lookup is keyed by letters/digits only, so both "BRK/B" and "BRK.B" resolve to "BRK.B".
SYMBOL_LOOKUP = {"AAPL": "AAPL", "BRKB": "BRK.B"}


def test_a_share_class_ticker_keeps_its_sector_after_switching_to_the_alpaca_symbol():
    holdings = [Holding(ticker="BRK/B", name="BERKSHIRE HATHAWAY INC CL B", weight=1.6)]

    universe = build_universe(
        holdings, sector_by_ticker={"BRK/B": "Financials"}, symbol_lookup=SYMBOL_LOOKUP
    )

    assert [(holding.ticker, holding.sector) for holding in universe] == [("BRK.B", "Financials")]


def test_holdings_alpaca_cannot_trade_are_left_out_of_the_universe():
    holdings = [
        Holding(ticker="AAPL", name="APPLE INC", weight=6.0),
        Holding(ticker="XYZ", name="NOT ON ALPACA", weight=0.1),
    ]

    universe = build_universe(
        holdings, sector_by_ticker={"AAPL": "Information Technology"}, symbol_lookup=SYMBOL_LOOKUP
    )

    assert [holding.ticker for holding in universe] == ["AAPL"]


def test_a_holding_missing_from_every_sector_fund_has_no_sector_rather_than_being_dropped():
    holdings = [Holding(ticker="AAPL", name="APPLE INC", weight=6.0)]

    universe = build_universe(holdings, sector_by_ticker={}, symbol_lookup=SYMBOL_LOOKUP)

    assert [(holding.ticker, holding.sector) for holding in universe] == [("AAPL", None)]
