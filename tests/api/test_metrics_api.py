from fastapi.testclient import TestClient

from stocktown.main import create_app


def test_the_metric_catalogue_lists_metrics_in_display_order_with_their_units():
    catalogue = TestClient(create_app(warm_on_startup=False)).get("/metrics").json()

    assert len(catalogue) == 7
    assert catalogue[0] == {
        "key": "one_year_return",
        "label": "1-year return",
        "unit": "percent",
        "scale": "percentile",
        "refresh": "daily",
    }
