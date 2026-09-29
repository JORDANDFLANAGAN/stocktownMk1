from fastapi.testclient import TestClient

from stocktown.main import create_app


def test_the_metric_catalogue_lists_metrics_in_display_order_with_their_units():
    catalogue = TestClient(create_app(warm_on_startup=False)).get("/api/metrics").json()

    assert len(catalogue) == 7
    assert catalogue[0] == {
        "key": "one_year_return",
        "label": "1-year return",
        "unit": "percent",
        "scale": "percentile",
        "refresh": "daily",
        "signed": True,
    }


def test_only_returns_are_signed_so_only_they_get_a_diverging_palette():
    catalogue = TestClient(create_app(warm_on_startup=False)).get("/api/metrics").json()

    signed_keys = {metric["key"] for metric in catalogue if metric["signed"]}

    assert signed_keys == {"one_year_return", "day_change"}
