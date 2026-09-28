from __future__ import annotations


class StocktownError(Exception):
    """Base for errors the API layer maps to HTTP responses."""


class UnknownUniverseError(StocktownError):
    def __init__(self, universe_id: str) -> None:
        super().__init__(f"Unknown universe {universe_id!r}")
        self.universe_id = universe_id


class UnknownTickerError(StocktownError):
    def __init__(self, ticker: str) -> None:
        super().__init__(f"Unknown ticker {ticker!r}")
        self.ticker = ticker


class UpstreamUnavailableError(StocktownError):
    """A data provider is down or rate-limiting us."""

    def __init__(self, provider: str, *, retry_after_seconds: int | None = None) -> None:
        super().__init__(f"{provider} is unavailable")
        self.provider = provider
        self.retry_after_seconds = retry_after_seconds
