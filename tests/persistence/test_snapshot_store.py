import sqlite3
from datetime import date, timedelta

from stocktown.domain.models import Holding, UniverseSnapshot
from stocktown.persistence import SnapshotStore
from stocktown.persistence.snapshot_store import KEPT_SNAPSHOTS_PER_UNIVERSE

DAY_ONE = date(2026, 9, 1)


def snapshot_built_on(built_on: date, *, universe_id: str = "spy") -> UniverseSnapshot:
    return UniverseSnapshot(
        universe_id=universe_id,
        built_on=built_on,
        session_date=built_on - timedelta(days=1),
        holdings=(
            Holding(ticker="AAPL", name="APPLE INC", weight=60.0, sector="Information Technology"),
            Holding(ticker="NSRGY", name="Nestlé S.A.", weight=40.0, sector=None),
        ),
        metric_values={"day_change": {"AAPL": 0.012, "NSRGY": None}},
        last_closes={"AAPL": 185.2, "NSRGY": None},
    )


def test_a_saved_snapshot_comes_back_unchanged_gaps_and_all(tmp_path):
    store = SnapshotStore(tmp_path / "stocktown.sqlite3")
    snapshot = snapshot_built_on(DAY_ONE)

    store.save(snapshot)

    assert store.latest("spy") == snapshot


def test_a_snapshot_with_no_session_yet_comes_back_without_one(tmp_path):
    store = SnapshotStore(tmp_path / "stocktown.sqlite3")
    snapshot = snapshot_built_on(DAY_ONE)
    no_session = UniverseSnapshot(
        universe_id=snapshot.universe_id,
        built_on=snapshot.built_on,
        session_date=None,
        holdings=snapshot.holdings,
        metric_values=snapshot.metric_values,
        last_closes=snapshot.last_closes,
    )

    store.save(no_session)

    assert store.latest("spy") == no_session


def test_latest_is_the_most_recently_built_whatever_order_they_were_saved_in(tmp_path):
    store = SnapshotStore(tmp_path / "stocktown.sqlite3")
    for days_later in (0, 2, 1):
        store.save(snapshot_built_on(DAY_ONE + timedelta(days=days_later)))

    assert store.latest("spy").built_on == DAY_ONE + timedelta(days=2)


def test_only_the_last_week_of_snapshots_is_kept(tmp_path):
    database_path = tmp_path / "stocktown.sqlite3"
    store = SnapshotStore(database_path)
    for days_later in range(KEPT_SNAPSHOTS_PER_UNIVERSE + 2):
        store.save(snapshot_built_on(DAY_ONE + timedelta(days=days_later)))

    with sqlite3.connect(database_path) as connection:
        kept = [row[0] for row in connection.execute("SELECT built_on FROM universe_snapshots")]

    assert sorted(kept) == [
        (DAY_ONE + timedelta(days=days_later)).isoformat()
        for days_later in range(2, KEPT_SNAPSHOTS_PER_UNIVERSE + 2)
    ]


def test_universes_do_not_see_each_others_snapshots(tmp_path):
    store = SnapshotStore(tmp_path / "stocktown.sqlite3")
    store.save(snapshot_built_on(DAY_ONE, universe_id="spy"))

    assert store.latest("my-portfolio") is None


def test_snapshots_survive_reopening_the_database(tmp_path):
    database_path = tmp_path / "stocktown.sqlite3"
    SnapshotStore(database_path).save(snapshot_built_on(DAY_ONE))

    reopened = SnapshotStore(database_path)

    assert reopened.latest("spy") == snapshot_built_on(DAY_ONE)
