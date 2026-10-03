from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stocktown.main import create_app

INDEX_HTML = "<!doctype html><div id=app></div>"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(INDEX_HTML)
    (tmp_path / "assets" / "app.js").write_text("console.log('town')")
    return TestClient(create_app(warm_on_startup=False, frontend_dir=tmp_path))


def test_a_deep_link_serves_the_app_so_the_router_can_resolve_it(client):
    response = client.get("/spy/town/ticker/AAPL")

    assert response.status_code == 200
    assert response.text == INDEX_HTML


def test_built_assets_are_served_as_themselves(client):
    assert client.get("/assets/app.js").text == "console.log('town')"


def test_api_routes_take_precedence_over_the_app(client):
    response = client.get("/api/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


def test_an_unknown_api_path_is_a_404_not_the_app(client):
    assert client.get("/api/no-such-endpoint").status_code == 404
