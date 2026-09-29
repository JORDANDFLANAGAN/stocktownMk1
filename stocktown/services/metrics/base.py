from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import ClassVar

from stocktown.services.metrics.market_data import MarketData

MetricValues = dict[str, float | None]


class Scale(Enum):
    """How the frontend maps raw values to height/colour, relative to the universe on screen."""

    LINEAR = "linear"
    LOG = "log"
    PERCENTILE = "percentile"


class Refresh(Enum):
    """How often the underlying data changes. Metadata for now; drives caching later."""

    LIVE = "live"
    DAILY = "daily"


class Unit(Enum):
    """Display unit. PERCENT values are stored as fractions (0.12 = 12%);
    RATIO values are plain multiples (1.2 = 1.2×)."""

    PERCENT = "percent"
    RATIO = "ratio"


class Metric(ABC):
    """A per-ticker value the city can map to height, colour or fill.

    Subclasses declare display metadata as class attributes and implement compute().
    compute() must return an entry for every ticker in data.tickers, using None when the
    value is unavailable or not meaningful (e.g. too little price history).
    """

    key: ClassVar[str]
    label: ClassVar[str]
    unit: ClassVar[Unit]
    scale: ClassVar[Scale]
    refresh: ClassVar[Refresh]
    # True when the sign is the point (gains vs losses): diverging palette centred on 0, "+" on gains.
    signed: ClassVar[bool]

    @abstractmethod
    def compute(self, data: MarketData) -> MetricValues: ...
