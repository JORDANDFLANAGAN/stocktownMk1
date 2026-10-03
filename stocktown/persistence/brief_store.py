from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Final

from stocktown.domain.models import CompanyBrief, NewsArticle

CREATE_SCHEMA: Final[str] = """
CREATE TABLE IF NOT EXISTS company_briefs (
    ticker   TEXT NOT NULL,
    made_on  TEXT NOT NULL,  -- ISO date, New York
    payload  TEXT NOT NULL,  -- the whole brief as JSON (brief_to_json)
    PRIMARY KEY (ticker, made_on)
)
"""


class BriefStore:
    """Today's AI briefs in SQLite, so a restart (or every save under `--reload`) doesn't spend
    Gemini's free quota again. Same connection approach as SnapshotStore."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(CREATE_SCHEMA)

    def get(self, ticker: str, *, made_on: date) -> CompanyBrief | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM company_briefs WHERE ticker = ? AND made_on = ?",
                (ticker, made_on.isoformat()),
            ).fetchone()
        return None if row is None else brief_from_json(row[0])

    def save(self, brief: CompanyBrief, *, made_on: date) -> None:
        """Also drops earlier days' briefs: once the day turns, they're never served again."""
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO company_briefs (ticker, made_on, payload) VALUES (?, ?, ?)",
                (brief.ticker, made_on.isoformat(), brief_to_json(brief)),
            )
            connection.execute(
                "DELETE FROM company_briefs WHERE made_on < ?", (made_on.isoformat(),)
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # A connection's own `with` commits (or rolls back) but doesn't close; closing() does that.
        with closing(sqlite3.connect(self._database_path)) as connection, connection:
            yield connection


def brief_to_json(brief: CompanyBrief) -> str:
    return json.dumps(
        {
            "ticker": brief.ticker,
            "about": brief.about,
            "news": list(brief.news),
            "sources": [
                {**asdict(article), "published_at": article.published_at.isoformat()}
                for article in brief.sources
            ],
            "model": brief.model,
        }
    )


def brief_from_json(payload: str) -> CompanyBrief:
    data: dict[str, Any] = json.loads(payload)
    return CompanyBrief(
        ticker=data["ticker"],
        about=data["about"],
        news=tuple(data["news"]),
        sources=tuple(
            NewsArticle(**{**source, "published_at": datetime.fromisoformat(source["published_at"])})
            for source in data["sources"]
        ),
        model=data["model"],
    )
