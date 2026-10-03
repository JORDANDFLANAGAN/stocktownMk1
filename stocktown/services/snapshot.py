from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable, Mapping
from datetime import date, timedelta
from typing import Final

from stocktown.domain.markets import today_in_new_york
from stocktown.domain.models import Holding, UniverseSnapshot
from stocktown.exceptions import UnknownUniverseError, UpstreamUnavailableError
from stocktown.persistence import SnapshotStore
from stocktown.providers.alpaca import load_daily_bars
from stocktown.services.metrics import MarketData, compute_metrics
from stocktown.services.metrics.market_data import DailyBarsLoader

# After a failed build, serve what we have (or 503) instead of rebuilding on every request.
RETRY_FAILED_BUILD_AFTER_SECONDS: Final[int] = 300

logger = logging.getLogger(__name__)

UniverseLoader = Callable[[], list[Holding]]


def start_daemon_thread(job: Callable[[], None]) -> None:
    threading.Thread(target=job, daemon=True).start()


class SnapshotService:
    """Builds each universe's snapshot once per New York day, keeps it in memory and (with a
    store) on disk, so a restart serves the last city at once.

    A stale snapshot (an earlier day's) is served straight away while one background rebuild
    replaces it. Only a universe with no snapshot at all makes a request wait for a build, and
    the lock makes concurrent first requests wait for a single one. A failed build keeps serving
    what we have, and isn't retried until RETRY_FAILED_BUILD_AFTER_SECONDS have passed.
    """

    def __init__(
        self,
        *,
        universe_loaders: Mapping[str, UniverseLoader],
        bars_loader: DailyBarsLoader = load_daily_bars,
        store: SnapshotStore | None = None,
        run_in_background: Callable[[Callable[[], None]], None] = start_daemon_thread,
        today: Callable[[], date] = today_in_new_york,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._universe_loaders = universe_loaders
        self._bars_loader = bars_loader
        self._store = store
        self._run_in_background = run_in_background
        self._today = today
        self._monotonic = monotonic
        self._snapshots: dict[str, UniverseSnapshot] = {}
        self._failed_at: dict[str, float] = {}
        self._rebuilding: set[str] = set()  # universes with a background rebuild in flight
        self._lock = threading.Lock()

    def get(self, universe_id: str) -> UniverseSnapshot:
        if universe_id not in self._universe_loaders:
            raise UnknownUniverseError(universe_id)

        with self._lock:
            cached = self._snapshots.get(universe_id) or self._load_stored(universe_id)
            if cached is None:
                return self._build_now(universe_id)  # nothing to show yet: this caller waits
            rebuild = cached.built_on != self._today() and self._may_rebuild(universe_id)
            if rebuild:
                self._rebuilding.add(universe_id)
        # Started outside the lock: the rebuild takes the lock itself when it's done.
        if rebuild:
            self._run_in_background(lambda: self._rebuild(universe_id))
        return cached

    def _build_now(self, universe_id: str) -> UniverseSnapshot:
        """With the lock held, so concurrent first requests wait for a single build."""
        seconds_until_retry = self._seconds_until_retry(universe_id)
        if seconds_until_retry > 0:
            raise UpstreamUnavailableError("market data", retry_after_seconds=seconds_until_retry)
        try:
            fresh = self._build(universe_id)
        except Exception:
            self._record_failure(universe_id)
            raise UpstreamUnavailableError(
                "market data", retry_after_seconds=RETRY_FAILED_BUILD_AFTER_SECONDS
            )
        self._keep(fresh)
        return fresh

    def _rebuild(self, universe_id: str) -> None:
        """In the background: builds without the lock, so requests keep getting the stale city."""
        try:
            fresh = self._build(universe_id)
        except Exception:
            with self._lock:
                self._record_failure(universe_id)
                self._rebuilding.discard(universe_id)
            return
        with self._lock:
            self._keep(fresh)
            self._rebuilding.discard(universe_id)

    def _may_rebuild(self, universe_id: str) -> bool:
        """At most one background rebuild per universe, and none during a failure's backoff."""
        return universe_id not in self._rebuilding and self._seconds_until_retry(universe_id) <= 0

    def _record_failure(self, universe_id: str) -> None:
        # Any provider or parser failure — SSGA's workbook format can change silently.
        logger.exception("Building the %s snapshot failed", universe_id)
        self._failed_at[universe_id] = self._monotonic()

    def _keep(self, snapshot: UniverseSnapshot) -> None:
        """With the lock held: serve it from now on, and store it for the next restart."""
        self._failed_at.pop(snapshot.universe_id, None)
        self._snapshots[snapshot.universe_id] = snapshot
        if self._store is None:
            return
        try:
            self._store.save(snapshot)
        except Exception:
            # The store is a cache: a full or read-only disk mustn't take the city down.
            logger.exception("Storing the %s snapshot failed", snapshot.universe_id)

    def _load_stored(self, universe_id: str) -> UniverseSnapshot | None:
        """The last city built before a restart, if the store has one."""
        if self._store is None:
            return None
        try:
            stored = self._store.latest(universe_id)
        except Exception:
            logger.exception("Reading the stored %s snapshot failed", universe_id)
            return None
        if stored is not None:
            self._snapshots[universe_id] = stored
        return stored

    def _seconds_until_retry(self, universe_id: str) -> int:
        failed_at = self._failed_at.get(universe_id)
        if failed_at is None:
            return 0
        return math.ceil(failed_at + RETRY_FAILED_BUILD_AFTER_SECONDS - self._monotonic())

    def _build(self, universe_id: str) -> UniverseSnapshot:
        holdings = self._universe_loaders[universe_id]()
        built_on = self._today()
        data = MarketData(
            [holding.ticker for holding in holdings],
            # Up to yesterday in New York, so today's unfinished session never enters the city.
            as_of=built_on - timedelta(days=1),
            bars_loader=self._bars_loader,
        )
        return UniverseSnapshot(
            universe_id=universe_id,
            built_on=built_on,
            session_date=data.latest_session,
            holdings=tuple(holdings),
            metric_values=compute_metrics(data),
            last_closes=last_closes(data),
        )


def last_closes(data: MarketData) -> dict[str, float | None]:
    """Each ticker's most recent close: the reference for the popup's live day change."""
    closes: dict[str, float | None] = {}
    for ticker in data.tickers:
        bars = data.daily_bars.get(ticker)
        closes[ticker] = bars[-1].close if bars else None
    return closes
