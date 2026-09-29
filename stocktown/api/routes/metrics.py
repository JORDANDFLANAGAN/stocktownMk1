from __future__ import annotations

from fastapi import APIRouter

from stocktown.api.schemas import MetricInfoResponse
from stocktown.services.metrics import ALL_METRICS

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
def list_metrics() -> list[MetricInfoResponse]:
    """The dropdown catalogue, in display order."""
    return [
        MetricInfoResponse(
            key=metric.key,
            label=metric.label,
            unit=metric.unit,
            scale=metric.scale,
            refresh=metric.refresh,
            signed=metric.signed,
        )
        for metric in ALL_METRICS
    ]
