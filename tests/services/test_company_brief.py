import random
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from stocktown.domain.models import NewsArticle, TradableAsset
from stocktown.exceptions import UpstreamUnavailableError
from stocktown.services.assets import AssetCatalogue
from stocktown.services.company_brief import CompanyBriefService
from tests.factories import FakeClock

APPLE = TradableAsset(
    symbol="AAPL", name="Apple Inc.", exchange="NASDAQ", asset_class="us_equity", tradable=True
)
FIRST_PUBLISHED = datetime(2026, 9, 26, 14, 0, tzinfo=UTC)

APPLE_REPLY = {
    "about": "Apple designs and sells iPhones, Macs and services.",
    "news": ["Apple is replacing some iPhones after a service-loss bug."],
    "article_numbers": [1],
}


def story(number: int) -> NewsArticle:
    """Story #00 is the oldest; each later one is published an hour after the previous."""
    return NewsArticle(
        headline=f"Story #{number:02d}",
        summary=f"Summary of story #{number:02d}.",
        source="Yahoo",
        url=f"https://example.com/story-{number:02d}",
        published_at=FIRST_PUBLISHED + timedelta(hours=number),
    )


def stories(count: int) -> list[NewsArticle]:
    """`count` stories in a shuffled order, so nothing relies on the order Finnhub sends."""
    articles = [story(number) for number in range(count)]
    random.Random(7).shuffle(articles)
    return articles


def rate_limited(url: str) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", url)
    response = httpx.Response(429, headers={"Retry-After": "30"}, request=request)
    return httpx.HTTPStatusError("Too Many Requests", request=request, response=response)


class FakeNews:
    def __init__(self, articles: list[NewsArticle], *, error: Exception | None = None) -> None:
        self.articles = articles
        self.error = error

    def __call__(self, ticker: str, *, until) -> list[NewsArticle]:
        if self.error is not None:
            raise self.error
        return self.articles


class FakeGemini:
    def __init__(self, reply: dict | None = None, *, error: Exception | None = None) -> None:
        self.reply = APPLE_REPLY if reply is None else reply
        self.error = error
        self.prompts: list[str] = []

    def __call__(self, *, system_instruction: str, prompt: str, response_schema: dict) -> dict:
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return self.reply


def build_service(
    *, news: FakeNews, gemini: FakeGemini, clock: FakeClock | None = None
) -> CompanyBriefService:
    return CompanyBriefService(
        assets=AssetCatalogue(assets_loader=lambda: [APPLE]),
        news_loader=news,
        generate=gemini,
        today=clock or FakeClock(),
    )


def test_the_prompt_numbers_only_the_twenty_newest_articles():
    gemini = FakeGemini()

    build_service(news=FakeNews(stories(25)), gemini=gemini).get("AAPL")

    prompt = gemini.prompts[0]
    assert "[1] 2026-09-27 · Yahoo · Story #24" in prompt  # newest first
    assert "[20] 2026-09-26 · Yahoo · Story #05" in prompt
    assert "Story #04" not in prompt


def test_sources_are_looked_up_from_our_articles_never_from_the_reply():
    articles = stories(3)
    reply = {**APPLE_REPLY, "article_numbers": [2, 99, 2, 0], "url": "https://evil.example"}

    brief = build_service(news=FakeNews(articles), gemini=FakeGemini(reply)).get("AAPL")

    second_newest = story(1)
    assert brief.sources == (second_newest,)


def test_without_news_the_brief_has_no_news_points_even_if_the_model_writes_some():
    gemini = FakeGemini({**APPLE_REPLY, "news": ["Apple bought the Moon."], "article_numbers": [1]})

    brief = build_service(news=FakeNews([]), gemini=gemini).get("AAPL")

    assert "No articles this week." in gemini.prompts[0]
    assert brief.about == APPLE_REPLY["about"]
    assert brief.news == ()
    assert brief.sources == ()


def test_a_brief_is_generated_once_per_ticker_per_new_york_day():
    gemini, clock = FakeGemini(), FakeClock()
    service = build_service(news=FakeNews(stories(3)), gemini=gemini, clock=clock)

    service.get("AAPL")
    service.get("aapl")
    assert len(gemini.prompts) == 1

    clock.advance_one_day()
    service.get("AAPL")
    assert len(gemini.prompts) == 2


def test_a_gemini_rate_limit_is_unavailable_with_retry_after():
    gemini = FakeGemini(error=rate_limited("https://generativelanguage.googleapis.com"))

    with pytest.raises(UpstreamUnavailableError) as raised:
        build_service(news=FakeNews(stories(3)), gemini=gemini).get("AAPL")

    assert raised.value.provider == "Gemini"
    assert raised.value.retry_after_seconds == 30


def test_a_reply_missing_fields_is_reported_as_gemini_unavailable():
    gemini = FakeGemini({"about": "Apple designs phones."})

    with pytest.raises(UpstreamUnavailableError) as raised:
        build_service(news=FakeNews(stories(3)), gemini=gemini).get("AAPL")

    assert raised.value.provider == "Gemini"


def test_a_news_outage_is_reported_as_finnhub_unavailable_without_asking_gemini():
    gemini = FakeGemini()
    news = FakeNews([], error=httpx.ConnectError("Finnhub unreachable"))

    with pytest.raises(UpstreamUnavailableError) as raised:
        build_service(news=news, gemini=gemini).get("AAPL")

    assert raised.value.provider == "Finnhub"
    assert gemini.prompts == []
