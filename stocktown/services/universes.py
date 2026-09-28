from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Final

from stocktown.domain.models import Holding
from stocktown.providers.alpaca import build_symbol_lookup, load_tradable_assets, resolve_tickers
from stocktown.providers.ssga import load_holdings, load_sector_map


@dataclass(frozen=True, slots=True)
class UniverseDefinition:
    id: str
    name: str
    load_holdings: Callable[[], list[Holding]]


def load_spy_holdings() -> list[Holding]:
    """SPY holdings with GICS sectors and Alpaca symbols, in weight order."""
    return build_universe(
        load_holdings(),
        sector_by_ticker=load_sector_map(),
        symbol_lookup=build_symbol_lookup(load_tradable_assets()),
    )


def load_spy_tickers() -> list[str]:
    """Alpaca symbols only — skips the sector downloads (used by the CLI preview)."""
    lookup = build_symbol_lookup(load_tradable_assets())
    return [holding.ticker for holding in with_canonical_tickers(load_holdings(), lookup)]


def build_universe(
    holdings: list[Holding],
    *,
    sector_by_ticker: dict[str, str],
    symbol_lookup: dict[str, str],
) -> list[Holding]:
    """Attach sectors, then switch to Alpaca symbols.

    Sectors are joined first, on SSGA's own ticker spelling, so punctuation differences
    between SSGA and Alpaca (e.g. share classes) can't lose a sector.
    """
    with_sectors = [
        replace(holding, sector=sector_by_ticker.get(holding.ticker)) for holding in holdings
    ]
    return with_canonical_tickers(with_sectors, symbol_lookup)


def with_canonical_tickers(holdings: list[Holding], symbol_lookup: dict[str, str]) -> list[Holding]:
    """Re-key holdings to Alpaca symbols; holdings Alpaca doesn't know are dropped."""
    resolved, _unresolved = resolve_tickers([holding.ticker for holding in holdings], symbol_lookup)
    return [
        replace(holding, ticker=resolved[holding.ticker])
        for holding in holdings
        if holding.ticker in resolved
    ]


UNIVERSES: Final[Mapping[str, UniverseDefinition]] = MappingProxyType(
    {"spy": UniverseDefinition(id="spy", name="S&P 500", load_holdings=load_spy_holdings)}
)
