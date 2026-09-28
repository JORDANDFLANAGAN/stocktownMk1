from __future__ import annotations

import threading
from collections.abc import Callable

import httpx

from stocktown.domain.models import TradableAsset
from stocktown.exceptions import UnknownTickerError, UpstreamUnavailableError
from stocktown.providers.alpaca import load_tradable_assets
from stocktown.providers.alpaca.assets import normalise_ticker


class AssetCatalogue:
    """Alpaca's tradable symbols, loaded on first use. Resolves any spelling of a ticker
    (BRK.B, brk-b, BRK/B) to its canonical asset, so every endpoint validates tickers alike."""

    def __init__(
        self, *, assets_loader: Callable[[], list[TradableAsset]] = load_tradable_assets
    ) -> None:
        self._load_assets = assets_loader
        self._assets_by_key: dict[str, TradableAsset] | None = None
        self._lock = threading.Lock()

    def find(self, ticker: str) -> TradableAsset:
        with self._lock:
            if self._assets_by_key is None:
                self._assets_by_key = self._load_assets_by_key()
            asset = self._assets_by_key.get(normalise_ticker(ticker))
        if asset is None:
            raise UnknownTickerError(ticker)
        return asset

    def _load_assets_by_key(self) -> dict[str, TradableAsset]:
        try:
            assets = self._load_assets()
        except httpx.HTTPError as error:
            raise UpstreamUnavailableError("Alpaca") from error
        return {normalise_ticker(asset.symbol): asset for asset in assets}
