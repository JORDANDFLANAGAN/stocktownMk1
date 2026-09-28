from __future__ import annotations

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
class MinuteBar:
    ticker: str
    minute_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
