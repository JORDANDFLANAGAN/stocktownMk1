from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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

# The 11 workbooks are independent downloads from SSGA's public site; fetching a few at a time
# cuts ~4s to ~1.3s without hammering it. Same number of downloads either way.
MAX_CONCURRENT_DOWNLOADS: Final[int] = 4


def load_sector_map() -> dict[str, str]:
    """Map each S&P 500 ticker (SSGA spelling) to its GICS sector."""
    fund_tickers = list(SECTOR_BY_FUND_TICKER)
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as pool:
        holdings_by_fund = pool.map(
            lambda fund_ticker: load_holdings(fund_holdings_url(fund_ticker)), fund_tickers
        )
        sector_by_ticker: dict[str, str] = {}
        for fund_ticker, holdings in zip(fund_tickers, holdings_by_fund):
            for holding in holdings:
                sector_by_ticker[holding.ticker] = SECTOR_BY_FUND_TICKER[fund_ticker]
    return sector_by_ticker
