import sqlite3
from datetime import UTC, date, datetime, timedelta

from stocktown.domain.models import CompanyBrief, NewsArticle
from stocktown.persistence import BriefStore

DAY_ONE = date(2026, 10, 2)

RECALL_STORY = NewsArticle(
    headline="Apple Says Some iPhone Users Must Replace Phones",
    summary="Apple said a small number of customers...",
    source="Yahoo",
    url="https://finnhub.io/api/news?id=b2ec",
    published_at=datetime(2026, 10, 2, 23, 3, 33, tzinfo=UTC),
)


def brief_for(ticker: str) -> CompanyBrief:
    return CompanyBrief(
        ticker=ticker,
        about="Designs and sells phones.",
        news=("Some phones are being replaced after a service-loss bug.",),
        sources=(RECALL_STORY,),
        model="gemini-3.8-flash",
    )


def test_a_saved_brief_comes_back_unchanged_sources_and_all(tmp_path):
    store = BriefStore(tmp_path / "stocktown.sqlite3")

    store.save(brief_for("AAPL"), made_on=DAY_ONE)

    assert store.get("AAPL", made_on=DAY_ONE) == brief_for("AAPL")


def test_a_brief_from_an_earlier_day_is_never_returned(tmp_path):
    store = BriefStore(tmp_path / "stocktown.sqlite3")

    store.save(brief_for("AAPL"), made_on=DAY_ONE)

    assert store.get("AAPL", made_on=DAY_ONE + timedelta(days=1)) is None


def test_saving_a_new_days_brief_drops_earlier_days(tmp_path):
    database_path = tmp_path / "stocktown.sqlite3"
    store = BriefStore(database_path)
    store.save(brief_for("AAPL"), made_on=DAY_ONE)
    store.save(brief_for("MSFT"), made_on=DAY_ONE)

    store.save(brief_for("AAPL"), made_on=DAY_ONE + timedelta(days=1))

    with sqlite3.connect(database_path) as connection:
        kept = list(connection.execute("SELECT ticker, made_on FROM company_briefs"))
    assert kept == [("AAPL", "2026-10-03")]
