from __future__ import annotations

import logging
import math
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Final
from zoneinfo import ZoneInfo

from stocktown.domain.models import Holding
from stocktown.exceptions import UnknownUniverseError, UpstreamUnavailableError
from stocktown.providers.alpaca import load_daily_bars
from stocktown.services.metrics import MarketData, MetricValues, compute_metrics
from stocktown.services.metrics.market_data import DailyBarsLoader

US_MARKET_TIMEZONE: Final = ZoneInfo("America/New_York")
# After a failed build, serve what we have (or 503) instead of rebuilding on every request.
RETRY_FAILED_BUILD_AFTER_SECONDS: Final[int] = 300

logger = logging.getLogger(__name__)

UniverseLoader = Callable[[], list[Holding]]


def today_in_new_york() -> date:
    return datetime.now(US_MARKET_TIMEZONE).date()


@dataclass(frozen=True, slots=True)
class UniverseSnapshot:
    universe_id: str
    built_on: date
    session_date: date | None  # the trading day the prices are from
    holdings: tuple[Holding, ...]
    metric_values: Mapping[str, MetricValues]  # metric key → ticker → value


class SnapshotService:
    """Builds each universe's snapshot once per New York day and serves it from memory.

    Stand-in for persistence: the lock makes concurrent first requests wait for a single
    build, a failed daily refresh keeps serving the previous snapshot, and a failure is not
    retried until RETRY_FAILED_BUILD_AFTER_SECONDS have passed.
    """

    def __init__(
        self,
        *,
        universe_loaders: Mapping[str, UniverseLoader],
        bars_loader: DailyBarsLoader = load_daily_bars,
        today: Callable[[], date] = today_in_new_york,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._universe_loaders = universe_loaders
        self._bars_loader = bars_loader
        self._today = today
        self._monotonic = monotonic
        self._snapshots: dict[str, UniverseSnapshot] = {}
        self._failed_at: dict[str, float] = {}
        self._lock = threading.Lock()

    def get(self, universe_id: str) -> UniverseSnapshot:
        if universe_id not in self._universe_loaders:
            raise UnknownUniverseError(universe_id)

        with self._lock:
            cached = self._snapshots.get(universe_id)
            if cached is not None and cached.built_on == self._today():
                return cached
            seconds_until_retry = self._seconds_until_retry(universe_id)
            if seconds_until_retry > 0:
                return stale_or_unavailable(cached, retry_after_seconds=seconds_until_retry)
            try:
                fresh = self._build(universe_id)
            except Exception:
                # Any provider or parser failure — SSGA's workbook format can change silently.
                logger.exception("Building the %s snapshot failed", universe_id)
                self._failed_at[universe_id] = self._monotonic()
                return stale_or_unavailable(
                    cached, retry_after_seconds=RETRY_FAILED_BUILD_AFTER_SECONDS
                )
            self._failed_at.pop(universe_id, None)
            self._snapshots[universe_id] = fresh
            return fresh

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
        )


def stale_or_unavailable(
    cached: UniverseSnapshot | None, *, retry_after_seconds: int
) -> UniverseSnapshot:
    if cached is None:
        raise UpstreamUnavailableError("market data", retry_after_seconds=retry_after_seconds)
    return cached  # stale but usable beats an empty city
