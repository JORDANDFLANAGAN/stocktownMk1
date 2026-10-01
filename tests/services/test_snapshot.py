import sqlite3
import threading
import time
from datetime import timedelta

import httpx
import pytest

from stocktown.domain.models import Holding
from stocktown.exceptions import UpstreamUnavailableError
from stocktown.persistence import SnapshotStore
from stocktown.services.snapshot import RETRY_FAILED_BUILD_AFTER_SECONDS, SnapshotService
from tests.factories import AS_OF, FakeClock, year_of_bars_loader

HOLDINGS = [
    Holding(ticker="AAPL", name="APPLE INC", weight=60.0, sector="Information Technology"),
    Holding(ticker="JPM", name="JPMORGAN CHASE & CO", weight=40.0, sector="Financials"),
]


class CountingUniverseLoader:
    def __init__(self, *, delay_seconds: float = 0.0) -> None:
        self.calls = 0
        self.delay_seconds = delay_seconds
        self.workbook_layout_changed = False

    def __call__(self) -> list[Holding]:
        self.calls += 1
        time.sleep(self.delay_seconds)
        if self.workbook_layout_changed:
            raise ValueError("Could not locate the header row in the SPY holdings workbook")
        return HOLDINGS


class FakeStopwatch:
    """Stands in for time.monotonic, so tests can skip past the retry backoff."""

    def __init__(self) -> None:
        self.seconds = 0.0

    def __call__(self) -> float:
        return self.seconds


class RecordingBarsLoader:
    def __init__(self) -> None:
        self.requested_end = None

    def __call__(self, tickers, *, start, end):
        self.requested_end = end
        return year_of_bars_loader(tickers, start=start, end=end)


class FlakyBarsLoader:
    """Serves normal bars until told Alpaca is down."""

    def __init__(self, *, alpaca_down: bool = False) -> None:
        self.alpaca_down = alpaca_down

    def __call__(self, tickers, *, start, end):
        if self.alpaca_down:
            raise httpx.ConnectError("Alpaca unreachable")
        return year_of_bars_loader(tickers, start=start, end=end)


class DeferredJobs:
    """Stands in for the background thread: holds each job until the test runs it."""

    def __init__(self) -> None:
        self.pending = []

    def __call__(self, job) -> None:
        self.pending.append(job)

    def run_all(self) -> None:
        jobs, self.pending = self.pending, []
        for job in jobs:
            job()


class BrokenStore:
    """A store whose disk has gone bad: every read and write fails."""

    def latest(self, universe_id):
        raise sqlite3.OperationalError("disk I/O error")

    def save(self, snapshot):
        raise sqlite3.OperationalError("disk I/O error")


def test_the_snapshot_is_built_once_and_reused_for_the_rest_of_the_day():
    loader = CountingUniverseLoader()
    service = SnapshotService(
        universe_loaders={"spy": loader}, bars_loader=year_of_bars_loader, today=FakeClock()
    )

    first = service.get("spy")
    second = service.get("spy")

    assert loader.calls == 1
    assert second is first


def test_a_new_day_serves_yesterdays_city_at_once_and_todays_once_the_rebuild_finishes():
    loader = CountingUniverseLoader()
    clock = FakeClock()
    jobs = DeferredJobs()
    service = SnapshotService(
        universe_loaders={"spy": loader},
        bars_loader=year_of_bars_loader,
        run_in_background=jobs,
        today=clock,
    )
    yesterdays = service.get("spy")
    clock.advance_one_day()

    assert service.get("spy") is yesterdays
    jobs.run_all()
    rebuilt = service.get("spy")

    assert loader.calls == 2
    assert rebuilt.built_on == clock.today


def test_every_new_day_gets_its_own_background_rebuild():
    clock = FakeClock()
    jobs = DeferredJobs()
    service = SnapshotService(
        universe_loaders={"spy": CountingUniverseLoader()},
        bars_loader=year_of_bars_loader,
        run_in_background=jobs,
        today=clock,
    )
    service.get("spy")

    for _ in range(2):
        clock.advance_one_day()
        service.get("spy")
        jobs.run_all()

    assert service.get("spy").built_on == clock.today


def test_only_one_background_rebuild_runs_at_a_time():
    clock = FakeClock()
    jobs = DeferredJobs()
    service = SnapshotService(
        universe_loaders={"spy": CountingUniverseLoader()},
        bars_loader=year_of_bars_loader,
        run_in_background=jobs,
        today=clock,
    )
    service.get("spy")
    clock.advance_one_day()

    for _ in range(3):
        service.get("spy")

    assert len(jobs.pending) == 1


def test_a_failed_background_rebuild_waits_for_the_backoff_before_trying_again():
    clock = FakeClock()
    bars_loader = FlakyBarsLoader()
    jobs = DeferredJobs()
    stopwatch = FakeStopwatch()
    service = SnapshotService(
        universe_loaders={"spy": CountingUniverseLoader()},
        bars_loader=bars_loader,
        run_in_background=jobs,
        today=clock,
        monotonic=stopwatch,
    )
    yesterdays = service.get("spy")
    clock.advance_one_day()
    bars_loader.alpaca_down = True
    service.get("spy")
    jobs.run_all()

    stopwatch.seconds = RETRY_FAILED_BUILD_AFTER_SECONDS - 1
    assert service.get("spy") is yesterdays
    assert jobs.pending == []

    stopwatch.seconds = RETRY_FAILED_BUILD_AFTER_SECONDS
    bars_loader.alpaca_down = False
    service.get("spy")
    jobs.run_all()
    assert service.get("spy").built_on == clock.today


def test_concurrent_first_requests_trigger_a_single_build():
    loader = CountingUniverseLoader(delay_seconds=0.05)
    service = SnapshotService(
        universe_loaders={"spy": loader}, bars_loader=year_of_bars_loader, today=FakeClock()
    )

    visitors = [threading.Thread(target=service.get, args=("spy",)) for _ in range(5)]
    for visitor in visitors:
        visitor.start()
    for visitor in visitors:
        visitor.join()

    assert loader.calls == 1


def test_if_a_refresh_fails_the_previous_snapshot_keeps_being_served():
    clock = FakeClock()
    bars_loader = FlakyBarsLoader()
    jobs = DeferredJobs()
    service = SnapshotService(
        universe_loaders={"spy": CountingUniverseLoader()},
        bars_loader=bars_loader,
        run_in_background=jobs,
        today=clock,
    )
    yesterdays = service.get("spy")

    bars_loader.alpaca_down = True
    clock.advance_one_day()
    service.get("spy")
    jobs.run_all()

    assert service.get("spy") is yesterdays


def test_if_the_first_build_fails_callers_get_upstream_unavailable():
    service = SnapshotService(
        universe_loaders={"spy": CountingUniverseLoader()},
        bars_loader=FlakyBarsLoader(alpaca_down=True),
        today=FakeClock(),
    )

    with pytest.raises(UpstreamUnavailableError) as raised:
        service.get("spy")

    assert raised.value.retry_after_seconds == RETRY_FAILED_BUILD_AFTER_SECONDS


def test_if_the_holdings_file_can_no_longer_be_parsed_the_previous_snapshot_keeps_being_served():
    clock = FakeClock()
    loader = CountingUniverseLoader()
    jobs = DeferredJobs()
    service = SnapshotService(
        universe_loaders={"spy": loader},
        bars_loader=year_of_bars_loader,
        run_in_background=jobs,
        today=clock,
    )
    yesterdays = service.get("spy")

    loader.workbook_layout_changed = True
    clock.advance_one_day()
    service.get("spy")
    jobs.run_all()

    assert service.get("spy") is yesterdays


def test_after_a_failed_build_requests_do_not_rebuild_until_the_backoff_passes():
    loader = CountingUniverseLoader()
    loader.workbook_layout_changed = True
    stopwatch = FakeStopwatch()
    service = SnapshotService(
        universe_loaders={"spy": loader},
        bars_loader=year_of_bars_loader,
        today=FakeClock(),
        monotonic=stopwatch,
    )

    for seconds_later in (0, 1, RETRY_FAILED_BUILD_AFTER_SECONDS - 1):
        stopwatch.seconds = seconds_later
        with pytest.raises(UpstreamUnavailableError):
            service.get("spy")
    assert loader.calls == 1

    stopwatch.seconds = RETRY_FAILED_BUILD_AFTER_SECONDS
    loader.workbook_layout_changed = False
    service.get("spy")
    assert loader.calls == 2


def test_during_the_backoff_retry_after_counts_down_to_the_next_attempt():
    loader = CountingUniverseLoader()
    loader.workbook_layout_changed = True
    stopwatch = FakeStopwatch()
    service = SnapshotService(
        universe_loaders={"spy": loader},
        bars_loader=year_of_bars_loader,
        today=FakeClock(),
        monotonic=stopwatch,
    )
    with pytest.raises(UpstreamUnavailableError):
        service.get("spy")

    stopwatch.seconds = 100
    with pytest.raises(UpstreamUnavailableError) as raised:
        service.get("spy")

    assert raised.value.retry_after_seconds == RETRY_FAILED_BUILD_AFTER_SECONDS - 100


def test_the_city_never_includes_todays_unfinished_session():
    bars_loader = RecordingBarsLoader()
    service = SnapshotService(
        universe_loaders={"spy": CountingUniverseLoader()},
        bars_loader=bars_loader,
        today=FakeClock(AS_OF),
    )

    service.get("spy")

    assert bars_loader.requested_end == AS_OF - timedelta(days=1)


def test_every_built_snapshot_is_stored(tmp_path):
    database_path = tmp_path / "stocktown.sqlite3"
    service = SnapshotService(
        universe_loaders={"spy": CountingUniverseLoader()},
        bars_loader=year_of_bars_loader,
        store=SnapshotStore(database_path),
        today=FakeClock(),
    )

    built = service.get("spy")

    assert SnapshotStore(database_path).latest("spy") == built


def test_a_restart_serves_the_stored_snapshot_without_building(tmp_path):
    database_path = tmp_path / "stocktown.sqlite3"
    before_restart = SnapshotService(
        universe_loaders={"spy": CountingUniverseLoader()},
        bars_loader=year_of_bars_loader,
        store=SnapshotStore(database_path),
        today=FakeClock(),
    ).get("spy")

    loader_after_restart = CountingUniverseLoader()
    after_restart = SnapshotService(
        universe_loaders={"spy": loader_after_restart},
        bars_loader=year_of_bars_loader,
        store=SnapshotStore(database_path),
        today=FakeClock(),
    )

    assert after_restart.get("spy") == before_restart
    assert loader_after_restart.calls == 0


def test_a_restart_on_a_later_day_serves_the_stored_city_while_rebuilding_and_stores_the_new_one(
    tmp_path,
):
    database_path = tmp_path / "stocktown.sqlite3"
    clock = FakeClock()
    stored = SnapshotService(
        universe_loaders={"spy": CountingUniverseLoader()},
        bars_loader=year_of_bars_loader,
        store=SnapshotStore(database_path),
        today=clock,
    ).get("spy")

    clock.advance_one_day()
    jobs = DeferredJobs()
    after_restart = SnapshotService(
        universe_loaders={"spy": CountingUniverseLoader()},
        bars_loader=year_of_bars_loader,
        store=SnapshotStore(database_path),
        run_in_background=jobs,
        today=clock,
    )

    assert after_restart.get("spy") == stored
    jobs.run_all()
    assert SnapshotStore(database_path).latest("spy").built_on == clock.today


def test_a_store_that_cannot_be_read_or_written_still_lets_the_city_be_built_and_served():
    loader = CountingUniverseLoader()
    service = SnapshotService(
        universe_loaders={"spy": loader},
        bars_loader=year_of_bars_loader,
        store=BrokenStore(),
        today=FakeClock(),
    )

    built = service.get("spy")

    assert service.get("spy") is built
    assert loader.calls == 1
