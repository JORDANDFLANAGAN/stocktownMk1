from datetime import UTC, datetime

from stocktown.providers.finnhub.news import parse_article

# One item as Finnhub's /company-news returned it on 2026-10-03 (summary shortened).
FINNHUB_ITEM = {
    "category": "company",
    "datetime": 1790982213,
    "headline": "Apple Says Some AT&T iPhone 18 Pro Max Users Must Replace Phones",
    "id": 142594315,
    "related": "AAPL",
    "source": "Yahoo",
    "summary": 'Apple (AAPL) said "a small number" of AT&T Inc. (T) customers...',
    "url": "https://finnhub.io/api/news?id=b2ec6db80654f30ce9067f1222936b7d",
}


def test_an_article_is_read_with_its_publication_time_in_utc():
    article = parse_article(FINNHUB_ITEM)

    assert article is not None
    assert article.source == "Yahoo"
    assert article.published_at == datetime(2026, 10, 2, 23, 3, 33, tzinfo=UTC)


def test_an_article_without_an_https_link_is_dropped():
    assert parse_article({**FINNHUB_ITEM, "url": "javascript:alert(1)"}) is None
    assert parse_article({**FINNHUB_ITEM, "url": "http://example.com/story"}) is None


def test_an_article_without_a_headline_or_time_is_dropped():
    assert parse_article({**FINNHUB_ITEM, "headline": ""}) is None
    assert parse_article({**FINNHUB_ITEM, "datetime": None}) is None
