from __future__ import annotations

from typing import Any, Final

import httpx

from stocktown.domain.models import TradableAsset
from stocktown.providers.alpaca.client import ALPACA_TRADING_BASE_URL, build_client

ASSETS_ENDPOINT: Final[str] = "/v2/assets"

US_EQUITY_ASSET_CLASS: Final[str] = "us_equity"
ACTIVE_STATUS: Final[str] = "active"


def load_tradable_assets() -> list[TradableAsset]:
    """Fetch every active US equity Alpaca currently supports."""

    with build_client(ALPACA_TRADING_BASE_URL) as client:
        return fetch_assets(client)


def fetch_assets(client: httpx.Client) -> list[TradableAsset]:
    response = client.get(
        ASSETS_ENDPOINT,
        params={"status": ACTIVE_STATUS, "asset_class": US_EQUITY_ASSET_CLASS},
    )
    response.raise_for_status()
    return [parse_asset(raw_asset) for raw_asset in response.json()]


def parse_asset(raw_asset: dict[str, Any]) -> TradableAsset:
    return TradableAsset(
        symbol=str(raw_asset["symbol"]),
        name=str(raw_asset.get("name", "")),
        exchange=str(raw_asset.get("exchange", "")),
        asset_class=str(raw_asset.get("class", "")),
        tradable=bool(raw_asset.get("tradable", False)),
    )


def build_symbol_lookup(assets: list[TradableAsset]) -> dict[str, str]:
    """Map a normalised key (letters/digits only, uppercase) to Alpaca's canonical symbol."""

    return {normalise_ticker(asset.symbol): asset.symbol for asset in assets}


def normalise_ticker(ticker: str) -> str:
    return "".join(character for character in ticker.upper() if character.isalnum())


def resolve_tickers(
    external_tickers: list[str],
    lookup: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    """Return (resolved_map, unresolved_list).

    resolved_map maps each external ticker (e.g. from the SPY file) to Alpaca's canonical
    symbol. unresolved_list holds any input ticker with no match — surface these for review.
    """

    resolved: dict[str, str] = {}
    unresolved: list[str] = []

    for ticker in external_tickers:
        canonical = lookup.get(normalise_ticker(ticker))
        if canonical is None:
            unresolved.append(ticker)
        else:
            resolved[ticker] = canonical

    return resolved, unresolved
