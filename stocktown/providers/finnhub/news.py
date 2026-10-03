from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any, Final

from stocktown.domain.models import NewsArticle
from stocktown.providers.finnhub.client import build_client

COMPANY_NEWS_ENDPOINT: Final[str] = "/company-news"
NEWS_LOOKBACK_DAYS: Final[int] = 7


def load_company_news(ticker: str, *, until: date) -> list[NewsArticle]:
    """The ticker's articles from the past week, in Finnhub's order."""
    since = until - timedelta(days=NEWS_LOOKBACK_DAYS)
    with build_client() as client:
        response = client.get(
            COMPANY_NEWS_ENDPOINT,
            params={"symbol": ticker, "from": since.isoformat(), "to": until.isoformat()},
        )
        response.raise_for_status()
    return [article for item in response.json() if (article := parse_article(item))]


def parse_article(item: dict[str, Any]) -> NewsArticle | None:
    """None for an item we can't show safely: no headline, no timestamp, or a non-https link."""
    headline, url, timestamp = item.get("headline"), item.get("url"), item.get("datetime")
    if not (headline and isinstance(url, str) and url.startswith("https://")):
        return None
    if not isinstance(timestamp, int):
        return None
    return NewsArticle(
        headline=str(headline),
        summary=str(item.get("summary") or ""),
        source=str(item.get("source") or ""),
        url=url,
        published_at=datetime.fromtimestamp(timestamp, tz=UTC),
    )
