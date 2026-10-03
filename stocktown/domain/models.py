from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class Holding:
    ticker: str
    name: str
    weight: float
    sector: str | None = None


@dataclass(frozen=True, slots=True)
class DailyBar:
    ticker: str
    trading_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True, slots=True)
class TradableAsset:
    symbol: str
    name: str
    exchange: str
    asset_class: str
    tradable: bool


@dataclass(frozen=True, slots=True)
class Fundamentals:
    ticker: str
    pe_ratio: float | None
    market_cap: float | None
    dividend_yield: float | None


@dataclass(frozen=True, slots=True)
class NewsArticle:
    headline: str
    summary: str
    source: str
    url: str
    published_at: datetime  # UTC


@dataclass(frozen=True, slots=True)
class MinuteBar:
    ticker: str
    minute_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True, slots=True)
class UniverseSnapshot:
    universe_id: str
    built_on: date  # the New York day it was built
    session_date: date | None  # the trading day the prices are from
    holdings: tuple[Holding, ...]
    metric_values: Mapping[str, Mapping[str, float | None]]  # metric key → ticker → value
    last_closes: Mapping[str, float | None]  # ticker → most recent close (None: no price history)
