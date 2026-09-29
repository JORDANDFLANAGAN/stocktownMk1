import pytest
from fastapi.testclient import TestClient

from stocktown.api.dependencies import get_snapshot_service
from stocktown.domain.models import Holding
from stocktown.main import create_app
from stocktown.services.metrics import ALL_METRICS
from stocktown.services.snapshot import SnapshotService
from tests.factories import FakeClock, year_of_bars_loader

# Weights as SSGA publishes them: percentages summing to 100.
HOLDINGS = [
    Holding(ticker="AAPL", name="APPLE INC", weight=60.0, sector="Information Technology"),
    Holding(ticker="JPM", name="JPMORGAN CHASE & CO", weight=40.0, sector="Financials"),
]
# Twenty equal holdings — enough JSON for gzip to kick in.
TWENTY_HOLDINGS = [
    Holding(ticker=f"T{index:02d}", name=f"COMPANY {index}", weight=5.0) for index in range(20)
]


def bars_for_all_but_newco(tickers, *, start, end):
    """NEWCO listed today: Alpaca has no price history for it yet."""
    bars = year_of_bars_loader(tickers, start=start, end=end)
    bars.pop("NEWCO", None)
    return bars


def client_for(holdings: list[Holding]) -> TestClient:
    app = create_app(warm_on_startup=False)
    snapshots = SnapshotService(
        universe_loaders={"spy": lambda: holdings},
        bars_loader=bars_for_all_but_newco,
        today=FakeClock(),
    )
    app.dependency_overrides[get_snapshot_service] = lambda: snapshots
    return TestClient(app)


def test_the_universe_lists_every_position_with_every_metric_key_including_nulls():
    newly_listed = Holding(ticker="NEWCO", name="NEWLY LISTED", weight=0.0)
    response = client_for(HOLDINGS + [newly_listed]).get("/api/universes/spy")

    positions = {position["ticker"]: position for position in response.json()["positions"]}
    metric_keys = {metric.key for metric in ALL_METRICS}

    assert response.status_code == 200
    assert positions.keys() == {"AAPL", "JPM", "NEWCO"}
    assert all(position["metrics"].keys() == metric_keys for position in positions.values())
    assert all(value is None for value in positions["NEWCO"]["metrics"].values())
    assert positions["AAPL"]["sector"] == "Information Technology"


def test_position_weights_are_fractions_that_sum_to_one():
    positions = client_for(HOLDINGS).get("/api/universes/spy").json()["positions"]

    assert [position["weight"] for position in positions] == pytest.approx([0.6, 0.4])


def test_an_unknown_universe_returns_404():
    response = client_for(HOLDINGS).get("/api/universes/ftse100")

    assert response.status_code == 404


def test_large_responses_are_gzipped():
    response = client_for(TWENTY_HOLDINGS).get(
        "/api/universes/spy", headers={"Accept-Encoding": "gzip"}
    )

    assert response.headers["content-encoding"] == "gzip"
