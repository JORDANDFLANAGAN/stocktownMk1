import httpx
from fastapi.testclient import TestClient

from stocktown.api.dependencies import get_instrument_service
from stocktown.domain.models import Fundamentals, TradableAsset
from stocktown.main import create_app
from stocktown.services.assets import AssetCatalogue
from stocktown.services.instruments import InstrumentService
from tests.factories import FakeClock

APPLE = TradableAsset(
    symbol="AAPL", name="Apple Inc.", exchange="NASDAQ", asset_class="us_equity", tradable=True
)


def fetch_apple(ticker: str) -> Fundamentals:
    return Fundamentals(ticker=ticker, pe_ratio=38.6, market_cap=4_977_637.0, dividend_yield=0.5)


def fetch_rate_limited(ticker: str) -> Fundamentals:
    request = httpx.Request("GET", "https://finnhub.io/api/v1/stock/metric")
    response = httpx.Response(429, headers={"Retry-After": "30"}, request=request)
    raise httpx.HTTPStatusError("Too Many Requests", request=request, response=response)


def alpaca_unreachable() -> list[TradableAsset]:
    raise httpx.ConnectError("Alpaca unreachable")


def client_with_finnhub(fundamentals_fetcher, *, assets_loader=lambda: [APPLE]) -> TestClient:
    app = create_app(warm_on_startup=False)
    instruments = InstrumentService(
        assets=AssetCatalogue(assets_loader=assets_loader),
        fundamentals_fetcher=fundamentals_fetcher,
        today=FakeClock(),
    )
    app.dependency_overrides[get_instrument_service] = lambda: instruments
    return TestClient(app)


def test_the_popup_receives_apples_fundamentals_by_ticker():
    response = client_with_finnhub(fetch_apple).get("/instruments/AAPL")

    assert response.status_code == 200
    assert response.json()["name"] == "Apple Inc."
    assert response.json()["market_cap_usd"] == 4_977_637_000_000.0


def test_an_unknown_ticker_returns_404():
    response = client_with_finnhub(fetch_apple).get("/instruments/NOTATICKER")

    assert response.status_code == 404


def test_a_rate_limited_popup_returns_503_with_retry_after():
    response = client_with_finnhub(fetch_rate_limited).get("/instruments/AAPL")

    assert response.status_code == 503
    assert response.headers["retry-after"] == "30"


def test_an_unreachable_asset_catalogue_returns_503_not_404():
    response = client_with_finnhub(fetch_apple, assets_loader=alpaca_unreachable).get(
        "/instruments/AAPL"
    )

    assert response.status_code == 503
