from __future__ import annotations

import io
import re
from typing import Final, Iterable

import httpx
import pandas as pd

from stocktown.domain.models import Holding

SSGA_HOLDINGS_URL_TEMPLATE: Final[str] = (
    "https://www.ssga.com/us/en/intermediary/library-content/"
    "products/fund-data/etfs/us/holdings-daily-us-en-{fund_ticker}.xlsx"
)


def fund_holdings_url(fund_ticker: str) -> str:
    return SSGA_HOLDINGS_URL_TEMPLATE.format(fund_ticker=fund_ticker.lower())


SPY_HOLDINGS_URL: Final[str] = fund_holdings_url("SPY")

DEFAULT_REQUEST_TIMEOUT_SECONDS: Final[float] = 30.0

SHARE_CLASS_SUFFIX: Final = re.compile(r"\s+(?:CL\.?|CLASS)\s+[A-Z]$", re.IGNORECASE)
VALID_TICKER: Final = re.compile(r"^[A-Z][A-Z0-9./-]*$")


def load_holdings(url: str = SPY_HOLDINGS_URL) -> list[Holding]:
    """Download the SPY holdings workbook and return normalised holdings."""

    workbook_bytes = download_workbook(url)
    return extract_holdings(workbook_bytes)


def download_workbook(
    url: str, *, timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS
) -> bytes:
    response = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
    response.raise_for_status()
    return response.content


def extract_holdings(workbook_bytes: bytes) -> list[Holding]:
    raw_sheet = read_raw_sheet(workbook_bytes)
    header_row = locate_header_row(raw_sheet)
    holdings_frame = read_holdings_frame(workbook_bytes, header_row=header_row)

    holdings_frame = clean_holding_rows(holdings_frame)
    holdings_frame = merge_share_classes(holdings_frame)
    holdings_frame = normalise_weights(holdings_frame)

    return frame_to_holdings(holdings_frame)


def read_raw_sheet(workbook_bytes: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(workbook_bytes), header=None, engine="openpyxl")


def locate_header_row(sheet: pd.DataFrame) -> int:
    for row_index, row in sheet.iterrows():
        cells = {str(value).strip().lower() for value in row.dropna()}
        looks_like_header = (
            "name" in cells
            and "ticker" in cells
            and any("weight" in cell for cell in cells)
        )
        if looks_like_header:
            return int(row_index)
    raise ValueError("Could not locate the header row in the SPY holdings workbook")


def read_holdings_frame(workbook_bytes: bytes, *, header_row: int) -> pd.DataFrame:
    frame = pd.read_excel(
        io.BytesIO(workbook_bytes), header=header_row, engine="openpyxl"
    )
    frame.columns = [str(column).strip() for column in frame.columns]

    column_renames = {
        find_column(frame.columns, keyword="name"): "name",
        find_column(frame.columns, keyword="ticker"): "ticker",
        find_column(frame.columns, keyword="weight"): "weight",
    }
    return frame.rename(columns=column_renames)[["name", "ticker", "weight"]]


def find_column(columns: Iterable[str], *, keyword: str) -> str:
    available = list(columns)
    for column in available:
        if keyword in column.lower():
            return column
    raise ValueError(f"No column containing '{keyword}' in {available}")


def clean_holding_rows(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.dropna(subset=["name", "ticker", "weight"]).copy()
    cleaned["ticker"] = cleaned["ticker"].astype(str).str.strip().str.upper()
    cleaned["name"] = cleaned["name"].astype(str).str.strip()
    cleaned["weight"] = pd.to_numeric(cleaned["weight"], errors="coerce")

    cleaned = cleaned.dropna(subset=["weight"])
    return cleaned[cleaned["ticker"].str.match(VALID_TICKER)]


def merge_share_classes(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["company_key"] = (
        frame["name"]
        .str.replace(SHARE_CLASS_SUFFIX, "", regex=True)
        .str.strip()
        .str.upper()
    )
    return (
        frame.sort_values("weight", ascending=False)
        .groupby("company_key", as_index=False)
        .agg(
            name=("name", "first"),
            ticker=("ticker", "first"),
            weight=("weight", "sum"),
        )
    )


def normalise_weights(frame: pd.DataFrame) -> pd.DataFrame:
    total_weight = frame["weight"].sum()
    if total_weight <= 0:
        raise ValueError(
            "Parsed weights sum to zero; the workbook layout may have changed"
        )

    normalised = frame.copy()
    normalised["weight"] = normalised["weight"] / total_weight * 100.0
    return normalised.sort_values("weight", ascending=False).reset_index(drop=True)


def frame_to_holdings(frame: pd.DataFrame) -> list[Holding]:
    return [
        Holding(ticker=row.ticker, name=row.name, weight=float(row.weight))
        for row in frame.itertuples(index=False)
    ]
