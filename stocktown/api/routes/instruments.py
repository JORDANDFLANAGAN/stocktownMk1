from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from stocktown.api.dependencies import get_instrument_service
from stocktown.api.schemas import InstrumentResponse
from stocktown.services.instruments import InstrumentService

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("/{ticker}")
def get_instrument(
    ticker: str,
    instruments: Annotated[InstrumentService, Depends(get_instrument_service)],
) -> InstrumentResponse:
    detail = instruments.get(ticker)
    return InstrumentResponse(
        ticker=detail.ticker,
        name=detail.name,
        pe_ratio=detail.pe_ratio,
        market_cap_usd=detail.market_cap_usd,
        dividend_yield=detail.dividend_yield,
        earnings_yield=detail.earnings_yield,
    )
