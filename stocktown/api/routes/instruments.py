from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from stocktown.api.dependencies import get_company_brief_service, get_instrument_service
from stocktown.api.schemas import BriefResponse, InstrumentResponse, NewsSourceResponse
from stocktown.services.company_brief import CompanyBriefService
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


@router.get("/{ticker}/brief")
def get_company_brief(
    ticker: str,
    briefs: Annotated[CompanyBriefService, Depends(get_company_brief_service)],
) -> BriefResponse:
    brief = briefs.get(ticker)
    return BriefResponse(
        ticker=brief.ticker,
        about=brief.about,
        news=list(brief.news),
        sources=[
            NewsSourceResponse(
                headline=article.headline,
                source=article.source,
                url=article.url,
                published_at=article.published_at,
            )
            for article in brief.sources
        ],
        model=brief.model,
    )
