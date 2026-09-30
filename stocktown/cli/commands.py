from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import asdict
from datetime import date, timedelta

from stocktown import (
    ALL_METRICS,
    METRICS_BY_KEY,
    DailyBar,
    Fundamentals,
    Holding,
    MarketData,
    MinuteBar,
    Unit,
    build_symbol_lookup,
    compute_metrics,
    get_metric,
    load_daily_bars,
    load_fundamentals,
    load_holdings,
    load_sector_map,
    load_spy_tickers,
    load_tradable_assets,
    resolve_tickers,
    stream_minute_bars,
)

TOP_HOLDINGS_TO_PRINT = 10
JSON_SAMPLE_SIZE = 3
DEFAULT_BAR_LOOKBACK_DAYS = 7
DEFAULT_PREVIEW_TICKERS = ("AAPL", "MSFT", "NVDA")
MAX_METRIC_ROWS_TO_PRINT = 25
METRIC_COLUMN_MIN_WIDTH = 10


def main() -> None:
    parser = argparse.ArgumentParser(prog="stocktown", description="Stocktown data preview")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("holdings", help="Preview SPY holdings (name, ticker, weight)")

    bars_parser = subparsers.add_parser(
        "bars", help="Preview Alpaca daily bars for one or more tickers"
    )
    bars_parser.add_argument(
        "tickers",
        nargs="*",
        default=list(DEFAULT_PREVIEW_TICKERS),
        help=f"Tickers to fetch (default: {' '.join(DEFAULT_PREVIEW_TICKERS)})",
    )
    bars_parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_BAR_LOOKBACK_DAYS,
        help=f"Lookback window in calendar days (default: {DEFAULT_BAR_LOOKBACK_DAYS})",
    )

    fundamentals_parser = subparsers.add_parser(
        "fundamentals",
        help="Preview Finnhub fundamentals (P/E, market cap, dividend yield)",
    )
    fundamentals_parser.add_argument(
        "tickers",
        nargs="*",
        default=list(DEFAULT_PREVIEW_TICKERS),
        help=f"Tickers to fetch (default: {' '.join(DEFAULT_PREVIEW_TICKERS)})",
    )

    stream_parser = subparsers.add_parser(
        "stream",
        help="Live minute bars from Alpaca's IEX WebSocket (Ctrl-C to stop)",
    )
    stream_parser.add_argument(
        "tickers",
        nargs="*",
        default=list(DEFAULT_PREVIEW_TICKERS),
        help=f"Tickers to subscribe to (default: {' '.join(DEFAULT_PREVIEW_TICKERS)})",
    )

    subparsers.add_parser(
        "verify",
        help="Reconcile SPY tickers against Alpaca's asset catalogue and confirm bars fetch",
    )

    metrics_parser = subparsers.add_parser(
        "metrics", help="Compute price-based metrics for tickers or the full SPY universe"
    )
    metrics_universe = metrics_parser.add_mutually_exclusive_group()
    metrics_universe.add_argument(
        "tickers",
        nargs="*",
        default=list(DEFAULT_PREVIEW_TICKERS),
        help=f"Tickers to compute (default: {' '.join(DEFAULT_PREVIEW_TICKERS)})",
    )
    metrics_universe.add_argument(
        "--spy", action="store_true", help="Use every SPY holding instead of the given tickers"
    )
    metrics_parser.add_argument(
        "--metric",
        dest="metric_keys",
        action="append",
        choices=list(METRICS_BY_KEY),
        help="Only compute this metric (repeatable; default: all)",
    )

    subparsers.add_parser(
        "openapi", help="Print the API's OpenAPI schema as JSON (feeds the frontend's gen:api)"
    )

    args = parser.parse_args()

    if args.command == "holdings":
        preview_holdings(load_holdings())
    elif args.command == "bars":
        end = date.today()
        start = end - timedelta(days=args.days)
        preview_bars(load_daily_bars(args.tickers, start=start, end=end))
    elif args.command == "fundamentals":
        preview_fundamentals(load_fundamentals(args.tickers))
    elif args.command == "stream":
        try:
            asyncio.run(preview_stream(args.tickers))
        except KeyboardInterrupt:
            print("\nStopped.")
    elif args.command == "verify":
        preview_verification()
    elif args.command == "metrics":
        tickers = load_spy_tickers() if args.spy else args.tickers
        preview_metrics(tickers, metric_keys=args.metric_keys)
    elif args.command == "openapi":
        preview_openapi()


def preview_holdings(holdings: list[Holding]) -> None:
    total_weight = sum(holding.weight for holding in holdings)
    print(f"Parsed {len(holdings)} holdings totalling {total_weight:.4f}%\n")

    print(f"Top {TOP_HOLDINGS_TO_PRINT} by weight:")
    for holding in holdings[:TOP_HOLDINGS_TO_PRINT]:
        print(f"  {holding.ticker:<6} {holding.weight:6.3f}%  {holding.name}")

    print(f"\nAs JSON (first {JSON_SAMPLE_SIZE}):")
    print(json.dumps([asdict(holding) for holding in holdings[:JSON_SAMPLE_SIZE]], indent=2))


def preview_bars(bars_by_ticker: dict[str, list[DailyBar]]) -> None:
    if not bars_by_ticker:
        print("No bars returned. Check tickers and date range.")
        return

    for ticker, bars in bars_by_ticker.items():
        print(f"\n{ticker} — {len(bars)} bars")
        for bar in bars:
            print(
                f"  {bar.trading_date}  "
                f"O {bar.open:>8.2f}  H {bar.high:>8.2f}  "
                f"L {bar.low:>8.2f}  C {bar.close:>8.2f}  "
                f"V {bar.volume:>12,}"
            )


def preview_fundamentals(fundamentals_by_ticker: dict[str, Fundamentals]) -> None:
    header = f"{'Ticker':<8} {'P/E':>8} {'Mkt Cap ($M)':>16} {'Div Yield':>10}"
    print(header)
    print("-" * len(header))
    for ticker, fundamentals in fundamentals_by_ticker.items():
        print(
            f"{ticker:<8} "
            f"{format_optional_number(fundamentals.pe_ratio, width=8, spec='.2f')} "
            f"{format_optional_number(fundamentals.market_cap, width=16, spec=',.0f')} "
            f"{format_optional_number(fundamentals.dividend_yield, width=10, spec='.2f', suffix='%')}"
        )


def format_optional_number(
    value: float | None, *, width: int, spec: str, suffix: str = ""
) -> str:
    if value is None:
        return f"{'—':>{width}}"
    numeric_width = width - len(suffix)
    return f"{value:>{numeric_width}{spec}}{suffix}"


async def preview_stream(tickers: list[str]) -> None:
    print(f"Subscribing to minute bars for: {', '.join(tickers)}")
    print("(Ctrl-C to stop. Bars only arrive during US market hours.)\n")

    header = (
        f"{'Minute (UTC)':<20} {'Ticker':<8} "
        f"{'Open':>8} {'High':>8} {'Low':>8} {'Close':>8} {'Volume':>10}"
    )
    print(header)
    print("-" * len(header))

    async for bar in stream_minute_bars(tickers):
        print_minute_bar(bar)


def print_minute_bar(bar: MinuteBar) -> None:
    print(
        f"{bar.minute_utc.strftime('%Y-%m-%d %H:%M:%S'):<20} "
        f"{bar.ticker:<8} "
        f"{bar.open:>8.2f} {bar.high:>8.2f} {bar.low:>8.2f} {bar.close:>8.2f} "
        f"{bar.volume:>10,}"
    )


def preview_verification() -> None:
    print("Loading SPY holdings...")
    holdings = load_holdings()
    holdings_by_ticker: dict[str, Holding] = {holding.ticker: holding for holding in holdings}
    print(f"  {len(holdings)} tickers from SPY file\n")

    print("Loading Alpaca tradable assets...")
    assets = load_tradable_assets()
    lookup = build_symbol_lookup(assets)
    print(f"  {len(assets)} active US equities on Alpaca\n")

    print("Resolving SPY tickers against Alpaca...")
    resolved, unresolved = resolve_tickers(list(holdings_by_ticker.keys()), lookup)
    resolution_rate = len(resolved) / len(holdings) * 100
    print(f"  Resolved:   {len(resolved):>3}/{len(holdings)} ({resolution_rate:.1f}%)")
    print(f"  Unresolved: {len(unresolved):>3}")

    renames = {
        spy_ticker: canonical
        for spy_ticker, canonical in resolved.items()
        if spy_ticker != canonical
    }
    if renames:
        print(f"\nSymbol renames ({len(renames)}):")
        for spy_ticker, canonical in renames.items():
            print(f"  {spy_ticker:<8} → {canonical:<8}  {holdings_by_ticker[spy_ticker].name}")

    if unresolved:
        print(f"\nUnresolved tickers ({len(unresolved)}):")
        for ticker in unresolved:
            print(f"  {ticker:<8}  {holdings_by_ticker[ticker].name}")

    print("\nLoading sector map from 11 Select Sector SPDR funds...")
    sector_by_ticker = load_sector_map()
    without_sector = [ticker for ticker in holdings_by_ticker if ticker not in sector_by_ticker]
    with_sector_count = len(holdings) - len(without_sector)
    print(f"  Sectors found for {with_sector_count}/{len(holdings)} SPY holdings")
    if without_sector:
        print(f"\nHoldings without a sector ({len(without_sector)}):")
        for ticker in without_sector:
            print(f"  {ticker:<8}  {holdings_by_ticker[ticker].name}")

    if not resolved:
        print("\nNo tickers resolved — skipping bars sanity check.")
        return

    top_holding = holdings[0]
    canonical = resolved.get(top_holding.ticker, top_holding.ticker)
    print(f"\nEnd-to-end sanity check: fetching bars for {canonical} ({top_holding.name})...")
    end = date.today()
    start = end - timedelta(days=DEFAULT_BAR_LOOKBACK_DAYS)
    bars = load_daily_bars([canonical], start=start, end=end).get(canonical, [])
    print(f"  Got {len(bars)} bars over {DEFAULT_BAR_LOOKBACK_DAYS} calendar days")
    if bars:
        latest_bar = bars[-1]
        print(f"  Latest: {latest_bar.trading_date}  close ${latest_bar.close:.2f}")


def preview_metrics(tickers: list[str], *, metric_keys: list[str] | None) -> None:
    metrics = tuple(get_metric(key) for key in metric_keys) if metric_keys else ALL_METRICS
    data = MarketData(tickers, as_of=date.today())

    started = time.perf_counter()
    values_by_metric = compute_metrics(data, metrics=metrics)
    elapsed_seconds = time.perf_counter() - started
    print(
        f"{len(metrics)} metrics × {len(tickers)} tickers in {elapsed_seconds:.1f}s (incl. fetch)\n"
    )

    column_widths = {
        metric.key: max(len(metric.key), METRIC_COLUMN_MIN_WIDTH) + 2 for metric in metrics
    }
    header = f"{'Ticker':<8}" + "".join(f"{key:>{width}}" for key, width in column_widths.items())
    print(header)
    print("-" * len(header))

    for ticker in tickers[:MAX_METRIC_ROWS_TO_PRINT]:
        cells = (
            format_metric_value(
                values_by_metric[metric.key][ticker],
                unit=metric.unit,
                width=column_widths[metric.key],
            )
            for metric in metrics
        )
        print(f"{ticker:<8}" + "".join(cells))
    if len(tickers) > MAX_METRIC_ROWS_TO_PRINT:
        print(f"... {len(tickers) - MAX_METRIC_ROWS_TO_PRINT} more")

    print("\nMissing values:")
    for metric in metrics:
        missing = sum(value is None for value in values_by_metric[metric.key].values())
        print(f"  {metric.key:<18} {missing:>4}/{len(tickers)}")


def preview_openapi() -> None:
    # Imported here so the other commands don't build the web app they never use.
    from stocktown.main import create_app

    print(json.dumps(create_app(warm_on_startup=False).openapi(), indent=2))


def format_metric_value(value: float | None, *, unit: Unit, width: int) -> str:
    if value is None:
        text = "—"
    elif unit is Unit.PERCENT:
        text = f"{value * 100:+.1f}%"
    else:
        text = f"{value:.2f}"
    return f"{text:>{width}}"
