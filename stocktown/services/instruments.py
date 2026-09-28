from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Final

import httpx

from stocktown.domain.models import Fundamentals, TradableAsset
from stocktown.exceptions import UpstreamUnavailableError
from stocktown.providers.finnhub import load_ticker_fundamentals
from stocktown.services.assets import AssetCatalogue

# Finnhub reports market cap in millions of USD and dividend yield as a percentage.
USD_PER_MILLION: Final[float] = 1_000_000.0
FRACTION_PER_PERCENT: Final[float] = 0.01
DEFAULT_RETRY_AFTER_SECONDS: Final[int] = 60
HTTP_TOO_MANY_REQUESTS: Final[int] = 429


@dataclass(frozen=True, slots=True)
class InstrumentDetail:
    ticker: str
    name: str
    pe_ratio: float | None  # None for loss-makers: a negative P/E isn't meaningful
    market_cap_usd: float | None
    dividend_yield: float | None  # fraction, 0.005 = 0.5%
    earnings_yield: float | None  # 1 / P/E as a fraction; negative for loss-makers


class InstrumentService:
    """Popup detail for one ticker: Finnhub fundamentals, cached per ticker per day."""

    def __init__(
        self,
        *,
        assets: AssetCatalogue,
        fundamentals_fetcher: Callable[[str], Fundamentals] = load_ticker_fundamentals,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._assets = assets
        self._fetch_fundamentals = fundamentals_fetcher
        self._today = today
        self._details: dict[str, tuple[date, InstrumentDetail]] = {}
        self._lock = threading.Lock()

    def get(self, ticker: str) -> InstrumentDetail:
        asset = self._assets.find(ticker)
        today = self._today()
        with self._lock:
            cached = self._details.get(asset.symbol)
        if cached is not None and cached[0] == today:
            return cached[1]

        detail = to_instrument_detail(asset, self._fetch_or_raise(asset.symbol))
        with self._lock:
            self._details[asset.symbol] = (today, detail)
        return detail

    def _fetch_or_raise(self, symbol: str) -> Fundamentals:
        try:
            return self._fetch_fundamentals(symbol)
        except httpx.HTTPStatusError as error:
            if error.response.status_code == HTTP_TOO_MANY_REQUESTS:
                raise UpstreamUnavailableError(
                    "Finnhub", retry_after_seconds=retry_after_seconds(error.response)
                ) from error
            raise UpstreamUnavailableError("Finnhub") from error
        except httpx.HTTPError as error:
            raise UpstreamUnavailableError("Finnhub") from error


def to_instrument_detail(asset: TradableAsset, fundamentals: Fundamentals) -> InstrumentDetail:
    pe_ratio = fundamentals.pe_ratio
    return InstrumentDetail(
        ticker=asset.symbol,
        name=asset.name,
        pe_ratio=pe_ratio if pe_ratio is not None and pe_ratio > 0 else None,
        market_cap_usd=scaled(fundamentals.market_cap, factor=USD_PER_MILLION),
        dividend_yield=scaled(fundamentals.dividend_yield, factor=FRACTION_PER_PERCENT),
        earnings_yield=1 / pe_ratio if pe_ratio else None,
    )


def scaled(value: float | None, *, factor: float) -> float | None:
    return None if value is None else value * factor


def retry_after_seconds(response: httpx.Response) -> int:
    header = response.headers.get("Retry-After", "")
    return int(header) if header.isdigit() else DEFAULT_RETRY_AFTER_SECONDS
