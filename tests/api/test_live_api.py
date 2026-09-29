import asyncio

import anyio
import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from stocktown.api.dependencies import get_asset_catalogue, get_latest_bar_loader, get_live_bar_hub
from stocktown.api.routes.live import forward_until_disconnect
from stocktown.domain.models import TradableAsset
from stocktown.main import create_app
from stocktown.services.assets import AssetCatalogue
from stocktown.services.live import LiveBarHub
from tests.fake_alpaca import FakeAlpaca, minute_bar

APPLE = TradableAsset(
    symbol="AAPL", name="Apple Inc.", exchange="NASDAQ", asset_class="us_equity", tradable=True
)
FRIDAYS_CLOSE = minute_bar("AAPL", close=340.0)
MONDAYS_FIRST_MINUTE = minute_bar("AAPL", close=341.0)


def load_fridays_close(ticker: str):
    return FRIDAYS_CLOSE


def latest_bar_unavailable(ticker: str):
    raise httpx.ConnectError("Alpaca REST unreachable")


def alpaca_unreachable() -> list[TradableAsset]:
    raise httpx.ConnectError("Alpaca unreachable")


def client_for(
    alpaca: FakeAlpaca, *, latest_bar_loader=load_fridays_close, assets_loader=lambda: [APPLE]
) -> TestClient:
    app = create_app(warm_on_startup=False)
    hub = LiveBarHub(connect_upstream=alpaca.connect, idle_disconnect_seconds=0.01)
    app.dependency_overrides[get_live_bar_hub] = lambda: hub
    app.dependency_overrides[get_asset_catalogue] = lambda: AssetCatalogue(assets_loader=assets_loader)
    app.dependency_overrides[get_latest_bar_loader] = lambda: latest_bar_loader
    return TestClient(app)


def test_the_popup_gets_the_latest_price_immediately_then_live_bars():
    alpaca = FakeAlpaca(scripted_bars=[MONDAYS_FIRST_MINUTE])

    with client_for(alpaca).websocket_connect("/api/live?ticker=aapl") as popup:
        first, second = popup.receive_json(), popup.receive_json()

    assert (first["type"], first["close"]) == ("bar", 340.0)
    assert (second["type"], second["close"]) == ("bar", 341.0)


def test_live_bars_still_arrive_when_the_latest_price_cannot_be_loaded():
    alpaca = FakeAlpaca(scripted_bars=[MONDAYS_FIRST_MINUTE])

    with client_for(alpaca, latest_bar_loader=latest_bar_unavailable).websocket_connect(
        "/api/live?ticker=AAPL"
    ) as popup:
        assert popup.receive_json()["close"] == 341.0


class ClosedPopup:
    """A browser socket that has already gone away."""

    async def receive(self) -> dict[str, str]:
        return {"type": "websocket.disconnect"}


@pytest.mark.anyio
async def test_forwarding_stops_when_the_popup_closes_even_while_no_bars_are_flowing():
    # Uvicorn doesn't cancel a handler when the browser leaves, so the handler must notice
    # itself — otherwise, with the market shut, it waits for a bar forever and leaks the viewer.
    market_closed: asyncio.Queue = asyncio.Queue()

    with anyio.fail_after(1):
        await forward_until_disconnect(ClosedPopup(), market_closed)


def test_an_unknown_ticker_is_refused_with_a_not_found_close_code():
    with pytest.raises(WebSocketDisconnect) as refused:
        with client_for(FakeAlpaca()).websocket_connect("/api/live?ticker=NOTATICKER") as popup:
            popup.receive_json()

    assert refused.value.code == 4404


def test_an_unreachable_asset_catalogue_closes_the_popup_with_an_upstream_unavailable_code():
    with pytest.raises(WebSocketDisconnect) as refused:
        with client_for(FakeAlpaca(), assets_loader=alpaca_unreachable).websocket_connect(
            "/api/live?ticker=AAPL"
        ) as popup:
            popup.receive_json()

    assert refused.value.code == 4503
