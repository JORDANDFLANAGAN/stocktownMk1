import httpx
import pytest

from stocktown.domain.models import Fundamentals, TradableAsset
from stocktown.exceptions import UnknownTickerError, UpstreamUnavailableError
from stocktown.services.assets import AssetCatalogue
from stocktown.services.instruments import InstrumentService
from tests.factories import FakeClock

ASSETS = [
    TradableAsset(symbol="AAPL", name="Apple Inc.", exchange="NASDAQ", asset_class="us_equity", tradable=True),
    TradableAsset(symbol="RIVN", name="Rivian Automotive", exchange="NASDAQ", asset_class="us_equity", tradable=True),
]

# Apple as Finnhub reported it on 2026-09-25: market cap in $M, dividend yield in %.
APPLE_FUNDAMENTALS = Fundamentals(
    ticker="AAPL", pe_ratio=38.6073, market_cap=4_977_637.0, dividend_yield=0.50534
)
LOSS_MAKER_FUNDAMENTALS = Fundamentals(
    ticker="RIVN", pe_ratio=-5.0, market_cap=12_000.0, dividend_yield=None
)


class FakeFinnhub:
    def __init__(self, *, rate_limited: bool = False) -> None:
        self.requested: list[str] = []
        self.rate_limited = rate_limited

    def __call__(self, ticker: str) -> Fundamentals:
        self.requested.append(ticker)
        if self.rate_limited:
            request = httpx.Request("GET", "https://finnhub.io/api/v1/stock/metric")
            response = httpx.Response(429, headers={"Retry-After": "30"}, request=request)
            raise httpx.HTTPStatusError("Too Many Requests", request=request, response=response)
        return {"AAPL": APPLE_FUNDAMENTALS, "RIVN": LOSS_MAKER_FUNDAMENTALS}[ticker]


def build_service(finnhub: FakeFinnhub) -> InstrumentService:
    return InstrumentService(
        assets=AssetCatalogue(assets_loader=lambda: ASSETS),
        fundamentals_fetcher=finnhub,
        today=FakeClock(),
    )


def test_market_cap_and_dividend_yield_are_converted_to_usd_and_fractions():
    detail = build_service(FakeFinnhub()).get("AAPL")

    assert detail.market_cap_usd == pytest.approx(4.977637e12)  # $4.98 trillion
    assert detail.dividend_yield == pytest.approx(0.0050534)  # 0.5%
    assert detail.earnings_yield == pytest.approx(1 / 38.6073)


def test_a_loss_making_company_has_no_pe_but_a_negative_earnings_yield():
    detail = build_service(FakeFinnhub()).get("RIVN")

    assert detail.pe_ratio is None
    assert detail.earnings_yield == pytest.approx(-0.20)


def test_a_second_request_for_the_same_ticker_on_the_same_day_does_not_call_finnhub():
    finnhub = FakeFinnhub()
    service = build_service(finnhub)

    service.get("AAPL")
    service.get("AAPL")

    assert finnhub.requested == ["AAPL"]


def test_an_unknown_ticker_is_rejected_without_calling_finnhub():
    finnhub = FakeFinnhub()

    with pytest.raises(UnknownTickerError):
        build_service(finnhub).get("NOTATICKER")

    assert finnhub.requested == []


def test_finnhub_rate_limiting_surfaces_as_upstream_unavailable_with_retry_after():
    with pytest.raises(UpstreamUnavailableError) as raised:
        build_service(FakeFinnhub(rate_limited=True)).get("AAPL")

    assert raised.value.retry_after_seconds == 30
