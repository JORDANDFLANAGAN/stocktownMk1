import random
import sqlite3
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from stocktown.domain.models import NewsArticle, TradableAsset
from stocktown.exceptions import UpstreamUnavailableError
from stocktown.persistence import BriefStore
from stocktown.services.assets import AssetCatalogue
from stocktown.services.company_brief import GEMINI_MODELS, CompanyBriefService
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


def http_error(status: int, *, headers: dict[str, str] | None = None) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://generativelanguage.googleapis.com")
    response = httpx.Response(status, headers=headers, request=request)
    return httpx.HTTPStatusError(f"HTTP {status}", request=request, response=response)


def rate_limited() -> httpx.HTTPStatusError:
    return http_error(429, headers={"Retry-After": "30"})


def overloaded() -> httpx.HTTPStatusError:
    return http_error(503)


class FakeNews:
    def __init__(self, articles: list[NewsArticle], *, error: Exception | None = None) -> None:
        self.articles = articles
        self.error = error

    def __call__(self, ticker: str, *, until) -> list[NewsArticle]:
        if self.error is not None:
            raise self.error
        return self.articles


class FakeGemini:
    """Answers `reply`; fails with `error` for every model, or per model with `errors`."""

    def __init__(
        self,
        reply: dict | None = None,
        *,
        error: Exception | None = None,
        errors: dict[str, Exception] | None = None,
    ) -> None:
        self.reply = APPLE_REPLY if reply is None else reply
        self.errors = errors or {}
        self.error = error
        self.prompts: list[str] = []
        self.models_asked: list[str] = []

    def __call__(
        self, *, model: str, system_instruction: str, prompt: str, response_schema: dict
    ) -> dict:
        self.prompts.append(prompt)
        self.models_asked.append(model)
        error = self.errors.get(model, self.error)
        if error is not None:
            raise error
        return self.reply


class BrokenStore:
    """A store whose disk has gone bad: every read and write fails."""

    def get(self, ticker, *, made_on):
        raise sqlite3.OperationalError("disk I/O error")

    def save(self, brief, *, made_on):
        raise sqlite3.OperationalError("disk I/O error")


def build_service(
    *, news: FakeNews, gemini: FakeGemini, clock: FakeClock | None = None, store=None
) -> CompanyBriefService:
    return CompanyBriefService(
        assets=AssetCatalogue(assets_loader=lambda: [APPLE]),
        news_loader=news,
        generate=gemini,
        today=clock or FakeClock(),
        store=store,
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


def test_when_every_model_is_out_of_quota_the_brief_is_unavailable_with_retry_after():
    gemini = FakeGemini(error=rate_limited())

    with pytest.raises(UpstreamUnavailableError) as raised:
        build_service(news=FakeNews(stories(3)), gemini=gemini).get("AAPL")

    assert gemini.models_asked == list(GEMINI_MODELS)  # quotas are per model
    assert raised.value.provider == "Gemini"
    assert raised.value.retry_after_seconds == 30


@pytest.mark.parametrize(
    "reply",
    [
        {"about": "Apple designs phones."},  # fields missing
        ["Apple designs phones."],  # not an object
        {"about": "  ", "news": [], "article_numbers": []},  # nothing to say
    ],
    ids=["fields-missing", "not-an-object", "blank-about"],
)
def test_an_unusable_reply_is_reported_as_gemini_unavailable(reply):
    gemini = FakeGemini(reply)

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


def test_a_restart_on_the_same_day_serves_the_stored_brief_without_asking_gemini(tmp_path):
    database_path = tmp_path / "stocktown.sqlite3"
    before_restart, after_restart = FakeGemini(), FakeGemini()
    brief = build_service(
        news=FakeNews(stories(3)), gemini=before_restart, store=BriefStore(database_path)
    ).get("AAPL")

    restarted = build_service(
        news=FakeNews(stories(3)), gemini=after_restart, store=BriefStore(database_path)
    )

    assert restarted.get("AAPL") == brief
    assert after_restart.prompts == []


def test_a_store_that_cannot_be_read_or_written_still_serves_briefs():
    gemini = FakeGemini()
    service = build_service(news=FakeNews(stories(3)), gemini=gemini, store=BrokenStore())

    brief = service.get("AAPL")

    assert brief.about == APPLE_REPLY["about"]
    assert service.get("AAPL") is brief
    assert len(gemini.prompts) == 1


def test_an_overloaded_model_falls_back_and_the_brief_names_the_model_that_answered():
    first_choice, fallback = GEMINI_MODELS
    gemini = FakeGemini(errors={first_choice: overloaded()})

    brief = build_service(news=FakeNews(stories(3)), gemini=gemini).get("AAPL")

    assert gemini.models_asked == [first_choice, fallback]
    assert brief.model == fallback
    assert brief.about == APPLE_REPLY["about"]


def test_when_every_model_is_overloaded_the_brief_is_unavailable():
    gemini = FakeGemini(error=overloaded())

    with pytest.raises(UpstreamUnavailableError) as raised:
        build_service(news=FakeNews(stories(3)), gemini=gemini).get("AAPL")

    assert raised.value.provider == "Gemini"
    assert gemini.models_asked == list(GEMINI_MODELS)


def test_a_rejected_request_is_not_retried_on_another_model():
    gemini = FakeGemini(error=http_error(400))

    with pytest.raises(UpstreamUnavailableError):
        build_service(news=FakeNews(stories(3)), gemini=gemini).get("AAPL")

    assert gemini.models_asked == [GEMINI_MODELS[0]]
