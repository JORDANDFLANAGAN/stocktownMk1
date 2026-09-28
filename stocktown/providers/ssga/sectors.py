from __future__ import annotations

from typing import Final

from stocktown.providers.ssga.spy_holdings import fund_holdings_url, load_holdings

# The 11 Select Sector SPDR funds partition the S&P 500 by GICS sector — every constituent
# appears in exactly one. SPY's own file has an empty sector column, so we derive it from these.
SECTOR_BY_FUND_TICKER: Final[dict[str, str]] = {
    "XLK": "Information Technology",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLC": "Communication Services",
}


def load_sector_map() -> dict[str, str]:
    """Map each S&P 500 ticker (SSGA spelling) to its GICS sector."""
    sector_by_ticker: dict[str, str] = {}
    for fund_ticker, sector in SECTOR_BY_FUND_TICKER.items():
        for holding in load_holdings(fund_holdings_url(fund_ticker)):
            sector_by_ticker[holding.ticker] = sector
    return sector_by_ticker
