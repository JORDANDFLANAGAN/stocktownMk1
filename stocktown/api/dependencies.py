from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from stocktown.config import get_database_path
from stocktown.domain.models import MinuteBar
from stocktown.persistence import BriefStore, SnapshotStore
from stocktown.providers.alpaca import load_latest_bar
from stocktown.services.assets import AssetCatalogue
from stocktown.services.company_brief import CompanyBriefService
from stocktown.services.instruments import InstrumentService
from stocktown.services.live import LiveBarHub
from stocktown.services.snapshot import SnapshotService
from stocktown.services.universes import UNIVERSES

LatestBarLoader = Callable[[str], MinuteBar | None]


@lru_cache(maxsize=1)
def get_snapshot_service() -> SnapshotService:
    return SnapshotService(
        universe_loaders={universe.id: universe.load_holdings for universe in UNIVERSES.values()},
        store=SnapshotStore(get_database_path()),
    )


@lru_cache(maxsize=1)
def get_asset_catalogue() -> AssetCatalogue:
    return AssetCatalogue()


@lru_cache(maxsize=1)
def get_instrument_service() -> InstrumentService:
    return InstrumentService(assets=get_asset_catalogue())


@lru_cache(maxsize=1)
def get_company_brief_service() -> CompanyBriefService:
    return CompanyBriefService(
        assets=get_asset_catalogue(), store=BriefStore(get_database_path())
    )


@lru_cache(maxsize=1)
def get_live_bar_hub() -> LiveBarHub:
    return LiveBarHub()


def get_latest_bar_loader() -> LatestBarLoader:
    return load_latest_bar
