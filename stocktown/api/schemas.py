from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

from stocktown.domain.markets import to_us_market_time, us_session_date
from stocktown.domain.models import MinuteBar
from stocktown.services.metrics import Refresh, Scale, Unit


class PositionResponse(BaseModel):
    ticker: str
    name: str
    asset_class: str  # "equity" for now; portfolios will add etf, option, commodity, ...
    sector: str | None
    weight: float  # fraction of the universe; all positions sum to 1.0
    last_close: float | None  # most recent close in the snapshot; None without price history
    metrics: dict[str, float | None]  # metric key → value (None renders as a hatched roof)


class UniverseResponse(BaseModel):
    id: str
    name: str
    session_date: date | None  # trading day the prices are from
    positions: list[PositionResponse]


class MetricInfoResponse(BaseModel):
    key: str
    label: str
    unit: Unit
    scale: Scale
    refresh: Refresh
    signed: bool  # gains vs losses: diverging palette, "+" on gains


class InstrumentResponse(BaseModel):
    ticker: str
    name: str
    pe_ratio: float | None
    market_cap_usd: float | None
    dividend_yield: float | None
    earnings_yield: float | None


class LiveBarMessage(BaseModel):
    """One minute of trading for the popup; `type` leaves room for status messages later."""

    type: Literal["bar"] = "bar"
    ticker: str
    minute_utc: datetime
    minute_market: datetime  # the same minute on the market's clock, with its offset, for display
    session_date: date  # the market's trading day for this bar, so clients need no time-zone logic
    open: float
    high: float
    low: float
    close: float
    volume: int

    @classmethod
    def from_bar(cls, bar: MinuteBar) -> LiveBarMessage:
        return cls(
            ticker=bar.ticker,
            minute_utc=bar.minute_utc,
            minute_market=to_us_market_time(bar.minute_utc),
            session_date=us_session_date(bar.minute_utc),
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )
