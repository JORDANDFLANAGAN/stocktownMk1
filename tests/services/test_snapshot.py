import threading
import time
from datetime import timedelta

import httpx
import pytest

from stocktown.domain.models import Holding
from stocktown.exceptions import UpstreamUnavailableError
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


def test_the_snapshot_is_built_once_and_reused_for_the_rest_of_the_day():
    loader = CountingUniverseLoader()
    service = SnapshotService(
        universe_loaders={"spy": loader}, bars_loader=year_of_bars_loader, today=FakeClock()
    )

    first = service.get("spy")
    second = service.get("spy")

    assert loader.calls == 1
    assert second is first


def test_a_new_day_rebuilds_the_snapshot():
    loader = CountingUniverseLoader()
    clock = FakeClock()
    service = SnapshotService(
        universe_loaders={"spy": loader}, bars_loader=year_of_bars_loader, today=clock
    )

    service.get("spy")
    clock.advance_one_day()
    rebuilt = service.get("spy")

    assert loader.calls == 2
    assert rebuilt.built_on == clock.today


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
    service = SnapshotService(
        universe_loaders={"spy": CountingUniverseLoader()}, bars_loader=bars_loader, today=clock
    )
    yesterdays = service.get("spy")

    bars_loader.alpaca_down = True
    clock.advance_one_day()

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
    service = SnapshotService(
        universe_loaders={"spy": loader}, bars_loader=year_of_bars_loader, today=clock
    )
    yesterdays = service.get("spy")

    loader.workbook_layout_changed = True
    clock.advance_one_day()

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
