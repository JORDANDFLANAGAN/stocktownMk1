"""Market time: instants are UTC everywhere; which trading day one belongs to is market-local."""

from __future__ import annotations

from datetime import date, datetime
from typing import Final
from zoneinfo import ZoneInfo

US_MARKET_TIMEZONE: Final = ZoneInfo("America/New_York")


def us_session_date(instant: datetime) -> date:
    """The US trading day an instant belongs to (its New York calendar date)."""
    return instant.astimezone(US_MARKET_TIMEZONE).date()
