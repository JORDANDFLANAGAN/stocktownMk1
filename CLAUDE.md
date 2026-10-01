# Stocktown — Session Context

Short handover doc so a new Claude session can pick up where the previous one left off. See `StockTownOutline.md` for the product vision (its implementation details can be outdated — **if docs disagree: CLAUDE.md > FrontendPlan.md > StockTownOutline.md**) and `README.md` for setup + CLI reference.

## What we're building

A 3D city visualisation of a stock index or portfolio where each holding is a building. Footprint = index/portfolio weight; height = a viewer-selectable metric; colour = sector. The S&P 500 is the MVP universe; the long-term goal is users importing their own portfolio (or another fund) and seeing it as a city. See `StockTownOutline.md` for the MVP scope, metric catalogue, and roadmap.

**Goal:** a job-application portfolio piece, not a business — rank work by demo impact (Outline § Goal).

## Where things stand

**Data layer: complete.** Every external data source needed for the MVP is implemented, verified end-to-end (`python -m stocktown verify` currently resolves 500/500 SPY tickers against Alpaca), and organised in a layered Spring-Boot-style structure.

**Metric layer: complete.** 7 price-based metrics in `services/metrics/`, computed from a single Alpaca fetch. Full S&P 500 × 7 metrics ≈ 5s (fetch; the maths is ~0.2s). Preview with `uv run python -m stocktown metrics [TICKERS... | --spy]`. Verified: beta of VOO/IVV vs SPY ≈ 1.00.

**Tests:** 91 backend (pytest, ~0.7s) + 154 frontend (Vitest), behavioural and mutation-checked.

**Tooling: uv.** `uv sync` to set up, `uv run …` to run, `uv add [--dev] <pkg>` for dependencies. `uv.lock` pins versions and is committed. Dev dependencies live in `[dependency-groups] dev` in `pyproject.toml`.

**REST API (Phase A): complete.** `uv run uvicorn stocktown.main:app --reload`. `GET /universes/spy` (all positions + sectors + all metrics, one payload), `GET /metrics`, `GET /instruments/{ticker}` (Finnhub popup data). `SnapshotService` (memory + SQLite store; built ~10s from scratch, rebuilt once per New York day, prices up to *yesterday* in New York so a partial session never enters the city; a stale snapshot is served at once while one background rebuild replaces it; any build failure keeps serving what we have, and failures back off 5 min before retrying).

**Sectors** come from the 11 Select Sector SPDR files (SPY's own sector column is empty) — 500/500 coverage.

**Live popup stream (Phase B): complete.** `WS /live?ticker=` sends the latest bar immediately, then minute bars. `LiveBarHub` (`services/live.py`) shares Alpaca's ONE allowed WebSocket connection across all popups: ref-counted per-ticker subscriptions, lazy connect, idle disconnect after 60s, reconnect + resubscribe with backoff, bounded per-viewer queues (drop oldest). `AssetCatalogue` (`services/assets.py`) resolves any ticker spelling for both popup endpoints. Verified live against Alpaca and a real uvicorn server.

**Frontend: MVP done** — Vue 3 + TypeScript + Vite in `frontend/`, following `FrontendPlan.md` (phased plan + global decisions; read it before frontend work). Phases 0–6 complete: typed API client, stores, routes, list (sort, sector/search filters, column picker), drawer (live price, metrics, fundamentals) and the Three.js town (height picker, sector colours, 3D / top-down, hover glow + tooltip, click → drawer, labels + legend); filter dimming deferred. Phase 7: keyboard navigation for the list only (one tab stop, arrow keys, focus back on drawer close); the rest (toasts, live-region price, empty states, favicon) set aside as low value at this stage.

**Persistence (phase 1): done.** `persistence/SnapshotStore`: each built snapshot stored in SQLite (`data/stocktown.sqlite3`, `STOCKTOWN_DB_PATH` overrides; last 7 days kept). Measured against a real server: first request after a restart 9.4s → 0.004s; on a new day the first request is instant with yesterday's prices and today's arrive once the background rebuild lands.

**To re-check during US market hours:** whether Alpaca's free-tier latest-bar endpoint is real-time on IEX or 15-min delayed (pre-market it correctly returns the previous close). If delayed, label the popup's first price.

## Provider status

| Source | Module | Purpose |
|---|---|---|
| SSGA SPY holdings XLSX | `providers/ssga/spy_holdings.py` | universe, weights, sectors |
| Alpaca REST daily bars | `providers/alpaca/prices.py` | all city metrics |
| Alpaca WebSocket | `providers/alpaca/stream.py` | live minute bars for detail popup |
| Alpaca `/v2/assets` | `providers/alpaca/assets.py` | ticker catalogue + normalisation |
| Finnhub REST | `providers/finnhub/fundamentals.py` | P/E, market cap, dividend yield — **stock-detail popup only**, fetched on click |

Shared HTTP factory: `providers/alpaca/client.py`. Credentials + settings: `config.py`.

## Key design decisions (with reasoning — respect these unless there's a specific reason to revisit)

- **Layered structure, not flat.** `domain/`, `providers/`, `services/`, `cli/` at the top. New layers (`api/`, `main.py`, `persistence/`, `exceptions.py`) are created *only when the first concrete file needs to live in them* — no empty scaffolding.
- **Public API is curated via `stocktown/__init__.py` re-exports.** External code writes `from stocktown import Holding, load_holdings, ...` without knowing internal paths. Sub-packages also re-export from their own `__init__.py`. Internal modules import from sub-packages directly (never `from stocktown import ...`) to avoid circular imports.
- **httpx for sync HTTP, `websockets` for the async WS.** httpx supports both sync and async in one library — sync used for batch jobs, async reserved for streams and request-path code.
- **Split-adjusted historical prices, not dividend-adjusted.** Matches Yahoo Finance / TradingView expectations (price return, not total return).
- **Popup-only realtime.** The city itself is a static per-session snapshot; the WebSocket is subscribed to only when the user clicks into a single stock's detail view. This dodges the "unlimited free-tier subscription" unknown entirely. If revisiting: user briefly wanted a live city, then explicitly reverted.
- **Time:** UTC in storage and transport; market-local (per exchange) for trading-day logic, done in the backend (`domain/markets.py`, e.g. each live bar's `session_date` and `minute_market`); market data on screen in market time with a zone label (ET); user-local time only for account activity. The frontend does no time-zone arithmetic.
- **Ticker normalisation via strip-and-uppercase.** Works because SPY and Alpaca share-class punctuation is the only variation. Currently 100% resolution on the S&P 500. Alpaca `/v2/assets` is the source of truth for canonical symbols.
- **Credentials are masked in `__repr__`.** `AlpacaCredentials`/`FinnhubCredentials` override `__repr__` to print `***`. Prevents accidental leaks via `print()`, logging, or debuggers. `.env` is gitignored.
- **No premature abstractions.** No `PriceProvider`/`ReferenceProvider` `Protocol` interfaces yet — we have exactly one implementation of each. Added when a second implementation arrives (Phase 3, European provider). Same reasoning for custom exceptions and the DB layer.
- **Concurrent fetching, capped at 4.** Alpaca bar batches and the 11 SSGA sector workbooks are independent requests, so they're fetched side by side via `ThreadPoolExecutor` (`MAX_CONCURRENT_BATCHES`, `MAX_CONCURRENT_DOWNLOADS`): cold snapshot build ~30s → ~10s, identical data, same request count (Alpaca free tier: 200/min). The stored snapshot now hides the cold build except on the very first run.
- **Persistence: stdlib `sqlite3`, no ORM.** One table, snapshot as a JSON payload (always read and written whole); one short-lived connection per call (thread-safe without locking); `CREATE TABLE IF NOT EXISTS` until the first schema change needs `PRAGMA user_version` migrations. The store is a cache: read/write failures are logged, never raised. `UniverseSnapshot` lives in `domain/` so persistence and services don't import each other. The background rebuild runner is injected (`run_in_background`) so tests run it deterministically.
- **Finnhub rate-limited via `time.sleep(1.1)` between calls.** Naïve but sufficient now that Finnhub is only called per clicked stock. Not extracted to a shared rate-limiter until a second rate-limited API needs one.
- **Two frontend views, one state.** A Three.js city and a sortable/filterable list, both rendering the same state: two Pinia stores (universe, fundamentals) and a live-bar composable, plus the URL (sort, filters, metric picks, selected ticker). Filters are shared (list filter dims/hides buildings); sort is list-only. Both open the same popup. Rows never stream — realtime stays popup-only. List is built first: quicker, and it verifies the data path and the numbers the city renders.
- **Vue 3, not React or Angular.** User knows Angular and doesn't want it; Vue's templates and `ref`/`computed` map closely to Angular, and `watch()` fits imperative Three.js updates better than React's re-render model. Three.js is plain imperative code in one component (no TresJS/R3F-style wrapper). Table: TanStack Table v9 — sorting and rendering; filtering is our own shared pure function.
- **CLI structure**: `python -m stocktown <command>` with argparse subcommands (`holdings`, `bars`, `fundamentals`, `stream`, `verify`, `metrics`, `openapi`). Each subcommand has a matching `preview_*` function in `cli/commands.py`. Keep new commands consistent with this shape. Business logic the API will also need (e.g. `load_spy_tickers`) lives in `services/`, not the CLI.

## Metric layer decisions

- **City metrics are price-only (Alpaca).** Finnhub is 1 call/sec with no bulk endpoint (~9 min for the S&P, ~33 min for a 2,000-stock fund), so fundamentals can't drive city-wide heights for arbitrary portfolios. They load on **click** (not hover — sweeping the mouse would burn the 60/min limit) in the detail popup, cached per ticker per day.
- **Metrics are per ticker, never per universe.** A metric doesn't know whether a ticker came from SPY or a user portfolio. Raw values are stored; scaling (`Scale`) is applied against whatever universe is on screen, so a value can be "high" in a portfolio and "average" in the S&P.
- **`MarketData`** is a lazy per-run cache: each source fetched once on first access. SPY (`BENCHMARK_TICKER`) rides along in the same batch — used for beta and for `latest_session` (the most recent trading day, so no market calendar is needed).
- **`compute()` returns an entry for every requested ticker.** `None` = unavailable (short history, stale/halted, missing). Partial data is normal, not an error — enables progressive loading later.
- **Percent values are fractions** (0.12 = 12%); `RATIO` values are plain multiples. The frontend formats.
- **Each metric = class (metadata) + module-level pure function (maths).** Tests target the pure function with hand-built bars — no mocks, no network.
- **Registry is an explicit tuple** (`ALL_METRICS`), not decorator auto-registration. `index_by_key` validates required attributes and unique keys at import (fail fast), and returns a read-only mapping.
- **Stdlib `statistics`, not NumPy.** ~250 bars × 500 tickers is fast in pure Python; fetch time dominates. Revisit only if profiling says so.
- **The snapshot uses `as_of` = yesterday in New York** (enforced in `SnapshotService._build`). Intraday, today's bar is partial and understates relative volume.
- **Weight is not a metric** — it's the footprint, supplied by the universe.

## Testing principles (user requirement — tests must provide real value)

- **Behavioural, not for coverage.** Test names read as spec lines (`test_a_halted_stock_does_not_report_an_old_move_as_todays_change`). Every test must be able to fail for a plausible bug; no tests of enums, trivial getters, or CLI formatting.
- **Hand-written data with known answers.** 2–4 bars where possible, so expected values are checkable by hand. Builders in `tests/factories.py`.
- **Test through public behaviour.** Internal helpers (`price_series`) are covered via the metrics that use them, not directly.
- **No mocks, no network.** Inject fakes via constructor params (e.g. `MarketData(bars_loader=...)`).
- **Verify value by mutation.** When adding tests, inject the bugs they claim to catch and confirm they fail. (Found one weak test this way: periodic synthetic returns hid a date-misalignment bug — test data now uses seeded irregular returns.)
- **pytest config:** `--import-mode=importlib`, `pythonpath = ["."]` — no `__init__.py` needed in `tests/`. `pytest-timeout` (10s) so a hanging test fails instead of blocking. Async tests: `@pytest.mark.anyio` (backend fixed to asyncio in `tests/conftest.py`).
- **`TestClient` ≠ uvicorn for WebSockets.** It cancels handlers when the client leaves (uvicorn doesn't — handlers must detect disconnect themselves) and reports close codes sent before `accept()` (uvicorn turns those into HTTP 403). WebSocket work is only "done" after a check against a real server with a real client.
- **Frontend:** Vitest + Testing Library. Fakes via `fakeApi`/`piniaWith` (`src/__tests__/fakeApi.ts`) and injected seams (`createApi({ fetch })`, `useLiveBar(ticker, openSocket)`, `createAppRouter(memoryHistory)`); whole-app specs via `renderAppAt`/`testPortfolioApi` (`src/__tests__/renderApp.ts`). Fakes behave like the real thing (the `FakeSocket` fires `onclose` after `close()`, which is what caught a bug). `flushPromises()` after navigation. UI is finally confirmed by the user in their own browser.
- **Fakes must actually exercise the failure path.** Twice a test passed against the bug it was named for because the fake never produced the condition (every ticker had bars; periodic returns hid misalignment). The mutation check is what caught both.

## Working preferences (learned from prior sessions — follow these)

- **User comes from a Java/Spring Boot background** and is (self-described) rusty on Python. When explaining Python concepts, use Spring/Java analogies. Example: `with` = try-with-resources, `@dataclass` = record, `lru_cache` = @Configuration singleton, module = .java file, package = folder (`__init__.py` only when it re-exports something).
- **User reviews all code before it is written.** Present proposed code as text in the chat and wait for an explicit "approve" or equivalent before using `Write`/`Edit`. Restructures, refactors, and multi-file changes especially.
- **Be concise.** No preamble, no closing summaries, no filler. Direct answers, short tables, minimal prose. Bullet points where they help.
- **Readability > cleverness.** User values "clear, readable, industry-ready code." Small named functions over dense one-liners, descriptive variable names, constants at top of module, keyword-only args for clarity. Same standard as the existing code.
- **Testability matters.** Prefer pure functions and dependency injection over hidden state. Every provider module already follows this — small helpers that take dependencies as parameters, easy to unit-test in isolation.
- **Performance matters** — but measure first; keep the single-fetch design.
- **Security by default.** Credentials never in logs / exceptions / `__repr__`. TLS everywhere (`https://`, `wss://`). `.env` gitignored. New secrets always go through `config.py`.
- **Ask before deleting or overwriting anything non-obvious.** Especially config, env, or files that might contain user work.
- **Senior-engineer PR review** after a batch of work is welcome — findings table by severity, then fix.

## Free-tier facts to remember

- **Alpaca**: IEX feed only on free. Absolute volumes are ~2-3% of true — use ratios only. Paper trading URL is `https://paper-api.alpaca.markets` (not `https://api.alpaca.markets` — that's live). Daily bars are batched 100 symbols/request — full S&P in a few seconds.
- **Finnhub**: 60 calls/min, US only, no bulk endpoint. Reported `marketCapitalization` is in **millions of USD**.
- **SPY file**: free, no auth, but URL/format could change silently — parser is defensive but not bulletproof.

## What's next (in order)

1. **Deploy:** public URL (FastAPI serving the built frontend; keys server-side). Check Alpaca/Finnhub terms for public display first.
2. **README as a landing page:** GIF, pitch, "Try it", architecture diagram, key decisions.
3. **Depth feature — what-if builder with fund look-through** (Outline § Portfolios and import): curated funds + direct stocks, pro-rata funding, effective weights, overlap/concentration panel.
4. **Provider parser tests** (optional, small): `extract_pe_ratio`, SPY workbook parsing, `normalise_ticker`.
5. **Frontend deferred:** filter dimming, the rest of Phase 7, CSV export, portfolio columns, select rows → highlight in city.
6. **Persistence phase 2** (when the what-if builder needs it): daily-bars store per ticker, fetched incrementally; re-fetch a ticker's history when the overlapping days' split-adjusted closes change (a split). Minute bars for replay: curated days only, if ever.

API decisions to respect: all endpoints under `/api` (page routes own the rest of the URL space); one payload per city (no `/metrics/{key}` endpoint); items are `positions` with `asset_class`; all units are fractions (weights sum to 1.0); unknown → 404, provider down → 503 + `Retry-After`; tests use `create_app(warm_on_startup=False)` + `dependency_overrides`. WebSocket: unknown ticker → accept then close `4404`; provider down → `4503`; messages carry a `type` field (`"bar"` now, room for `"status"`).

Known deprecation: FastAPI's `TestClient` warns that `httpx` is deprecated for it in favour of `httpx2` — unverified; check on the next dependency update.

## Ideas parked for later

- **SEC EDGAR XBRL "frames" API** — possible free bulk source (one request = one figure for every US filer) for P/E and market cap, which would let fundamentals drive the city. Needs CIK↔ticker mapping and TTM summing. Unverified — needs a spike.
- **Nightly full-US Finnhub sweep + progressive loading** (weight order, hatched roofs filling in) if Finnhub data is ever needed city-wide.
- **Popup earnings fill:** 1/P/E (earnings yield) as the filled proportion of the building's height — works on any height metric.
- **Portfolio-mode metrics:** contribution to return (weight × return), position P&L (needs cost basis). In portfolio mode market cap as height becomes meaningful (footprint is position size, not market cap).
- **Live metrics:** live day change and relative volume from minute bars.
- **Stale-bar gating** currently applies to day change and relative volume only; 1-year metrics deliberately use a halted stock's last close.
