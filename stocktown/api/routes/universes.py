from __future__ import annotations

from typing import Annotated, Final

from fastapi import APIRouter, Depends

from stocktown.api.dependencies import get_snapshot_service
from stocktown.api.schemas import PositionResponse, UniverseResponse
from stocktown.domain.models import Holding
from stocktown.services.snapshot import SnapshotService, UniverseSnapshot
from stocktown.services.universes import UNIVERSES

EQUITY_ASSET_CLASS: Final[str] = "equity"
FRACTION_PER_PERCENT: Final[float] = 0.01

router = APIRouter(prefix="/universes", tags=["universes"])


@router.get("/{universe_id}")
def get_universe(
    universe_id: str,
    snapshots: Annotated[SnapshotService, Depends(get_snapshot_service)],
) -> UniverseResponse:
    snapshot = snapshots.get(universe_id)
    return to_universe_response(snapshot, name=UNIVERSES[universe_id].name)


def to_universe_response(snapshot: UniverseSnapshot, *, name: str) -> UniverseResponse:
    return UniverseResponse(
        id=snapshot.universe_id,
        name=name,
        session_date=snapshot.session_date,
        positions=[to_position_response(holding, snapshot) for holding in snapshot.holdings],
    )


def to_position_response(holding: Holding, snapshot: UniverseSnapshot) -> PositionResponse:
    return PositionResponse(
        ticker=holding.ticker,
        name=holding.name,
        asset_class=EQUITY_ASSET_CLASS,
        sector=holding.sector,
        weight=holding.weight * FRACTION_PER_PERCENT,
        last_close=snapshot.last_closes.get(holding.ticker),
        metrics={key: values.get(holding.ticker) for key, values in snapshot.metric_values.items()},
    )
