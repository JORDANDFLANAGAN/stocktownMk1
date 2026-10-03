from datetime import UTC, datetime

from fastapi.testclient import TestClient

from stocktown.api.dependencies import get_company_brief_service
from stocktown.domain.models import NewsArticle, TradableAsset
from stocktown.main import create_app
from stocktown.services.assets import AssetCatalogue
from stocktown.services.company_brief import CompanyBriefService
from tests.factories import FakeClock

APPLE = TradableAsset(
    symbol="AAPL", name="Apple Inc.", exchange="NASDAQ", asset_class="us_equity", tradable=True
)
RECALL_STORY = NewsArticle(
    headline="Apple Says Some iPhone Users Must Replace Phones",
    summary="Apple said a small number of customers...",
    source="Yahoo",
    url="https://finnhub.io/api/news?id=b2ec",
    published_at=datetime(2026, 10, 2, 22, 23, 33, tzinfo=UTC),
)


def generate_apple_brief(*, model, system_instruction, prompt, response_schema) -> dict:
    return {
        "about": "Apple designs and sells iPhones, Macs and services.",
        "news": ["Apple is replacing some iPhones after a service-loss bug."],
        "article_numbers": [1],
    }


def client() -> TestClient:
    app = create_app(warm_on_startup=False, frontend_dir=None)
    briefs = CompanyBriefService(
        assets=AssetCatalogue(assets_loader=lambda: [APPLE]),
        news_loader=lambda ticker, *, until: [RECALL_STORY],
        generate=generate_apple_brief,
        today=FakeClock(),
    )
    app.dependency_overrides[get_company_brief_service] = lambda: briefs
    return TestClient(app)


def test_the_popup_receives_a_brief_with_the_articles_it_relies_on():
    response = client().get("/api/instruments/AAPL/brief")

    assert response.status_code == 200
    assert response.json() == {
        "ticker": "AAPL",
        "about": "Apple designs and sells iPhones, Macs and services.",
        "news": ["Apple is replacing some iPhones after a service-loss bug."],
        "sources": [
            {
                "headline": "Apple Says Some iPhone Users Must Replace Phones",
                "source": "Yahoo",
                "url": "https://finnhub.io/api/news?id=b2ec",
                "published_at": "2026-10-02T22:23:33Z",
            }
        ],
        "model": "gemini-3.8-flash",
    }


def test_a_brief_for_an_unknown_ticker_returns_404():
    assert client().get("/api/instruments/NOTATICKER/brief").status_code == 404
