from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any, Final

from stocktown.domain.models import Holding, UniverseSnapshot

# Older snapshots are pruned on save: a week covers a long weekend plus a failed day or two.
KEPT_SNAPSHOTS_PER_UNIVERSE: Final[int] = 7

CREATE_SCHEMA: Final[str] = """
CREATE TABLE IF NOT EXISTS universe_snapshots (
    universe_id TEXT NOT NULL,
    built_on    TEXT NOT NULL,  -- ISO date, New York
    payload     TEXT NOT NULL,  -- the whole snapshot as JSON (snapshot_to_json)
    PRIMARY KEY (universe_id, built_on)
)
"""


class SnapshotStore:
    """Built snapshots in SQLite, so a restart serves the last city at once instead of rebuilding.

    One short-lived connection per call: SQLite connects in microseconds, and it keeps the store
    safe to use from request threads and the background rebuild alike.
    """

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(CREATE_SCHEMA)

    def latest(self, universe_id: str) -> UniverseSnapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM universe_snapshots WHERE universe_id = ? "
                "ORDER BY built_on DESC LIMIT 1",
                (universe_id,),
            ).fetchone()
        return None if row is None else snapshot_from_json(row[0])

    def save(self, snapshot: UniverseSnapshot) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO universe_snapshots (universe_id, built_on, payload) "
                "VALUES (?, ?, ?)",
                (snapshot.universe_id, snapshot.built_on.isoformat(), snapshot_to_json(snapshot)),
            )
            connection.execute(
                "DELETE FROM universe_snapshots WHERE universe_id = ? AND built_on NOT IN "
                "(SELECT built_on FROM universe_snapshots WHERE universe_id = ? "
                "ORDER BY built_on DESC LIMIT ?)",
                (snapshot.universe_id, snapshot.universe_id, KEPT_SNAPSHOTS_PER_UNIVERSE),
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # A connection's own `with` commits (or rolls back) but doesn't close; closing() does that.
        with closing(sqlite3.connect(self._database_path)) as connection, connection:
            yield connection


def snapshot_to_json(snapshot: UniverseSnapshot) -> str:
    return json.dumps(
        {
            "universe_id": snapshot.universe_id,
            "built_on": snapshot.built_on.isoformat(),
            "session_date": _iso_or_none(snapshot.session_date),
            "holdings": [asdict(holding) for holding in snapshot.holdings],
            "metric_values": {key: dict(values) for key, values in snapshot.metric_values.items()},
            "last_closes": dict(snapshot.last_closes),
        }
    )


def snapshot_from_json(payload: str) -> UniverseSnapshot:
    data: dict[str, Any] = json.loads(payload)
    return UniverseSnapshot(
        universe_id=data["universe_id"],
        built_on=date.fromisoformat(data["built_on"]),
        session_date=_date_or_none(data["session_date"]),
        holdings=tuple(Holding(**holding) for holding in data["holdings"]),
        metric_values=data["metric_values"],
        last_closes=data["last_closes"],
    )


def _iso_or_none(value: date | None) -> str | None:
    return None if value is None else value.isoformat()


def _date_or_none(value: str | None) -> date | None:
    return None if value is None else date.fromisoformat(value)
