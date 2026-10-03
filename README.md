# Stocktown

A 3D city visualisation of a stock index or portfolio, where each holding is a building. Footprint = index weight, height and colour = viewer-selectable metrics (1-year return, volatility, today's move, etc.). A second, list view shows the same data as a sortable, filterable table.

The MVP renders the S&P 500 as a treemap city and as a list, with a live detail view for any clicked-in stock in either. Later phases let users import their own portfolio or fund. See `StockTownOutline.md` for the full plan.

## Status

Backend MVP complete: data layer, metric layer, REST API and the live popup stream (`WS /live`). Frontend in progress: the list view is done; next the detail drawer, then the Three.js city. Persistence comes after a working frontend.

| Data | Source | Provider module |
|---|---|---|
| Index constituents, weights | SSGA SPY daily holdings file (free, no key) | `providers.ssga` |
| GICS sectors | SSGA Select Sector SPDR files (XLK, XLF, … — 11 funds that partition the S&P 500) | `providers.ssga.sectors` |
| Historical daily bars (all city metrics) | Alpaca Market Data REST | `providers.alpaca.prices` |
| Live minute bars (detail-view stream) | Alpaca Market Data WebSocket | `providers.alpaca.stream` |
| Tradable-symbol catalogue + ticker reconciliation | Alpaca Trading API | `providers.alpaca.assets` |
| Fundamentals (P/E, market cap, dividend yield) — stock-detail popup only | Finnhub REST | `providers.finnhub` |

City metrics (all computed from one Alpaca daily-bars fetch; full S&P 500 in ~5s — bar batches are fetched 4 at a time):

| Metric key | Meaning |
|---|---|
| `one_year_return` | Price return over 1 year |
| `day_change` | Latest session's % change |
| `volatility_30d` | Annualised 30-day volatility |
| `max_drawdown_1y` | Worst 1-year peak-to-trough fall |
| `off_52_week_high` | Distance below the 52-week high |
| `beta_1y` | Sensitivity to the S&P 500 (SPY) |
| `relative_volume` | Latest volume ÷ 20-day average |

## Setup

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/) (`brew install uv`).

```bash
uv sync            # creates .venv, installs runtime + dev dependencies pinned by uv.lock

# create .env (gitignored) with your keys:
#   ALPACA_API_KEY=...
#   ALPACA_API_SECRET=...
#   FINNHUB_API_KEY=...
```

Add a dependency with `uv add <package>` (or `uv add --dev <package>` for test/dev tools); this updates both `pyproject.toml` and `uv.lock`. Commit `uv.lock`.

- Alpaca paper-trading keys: <https://app.alpaca.markets/paper/dashboard/overview>
- Finnhub free API key: <https://finnhub.io/dashboard>

## API server

```bash
uv run uvicorn stocktown.main:app --reload
```

Interactive docs at <http://localhost:8000/docs>. On startup the S&P 500 snapshot builds in the background (~10s, varies with Alpaca); after that responses come from memory, and the snapshot rebuilds once per day. Bar batches and the 11 sector workbooks are fetched 4 at a time: same request count, well inside the free tiers.

Every endpoint lives under `/api`; the design notes below omit the prefix.

| Endpoint | Returns |
|---|---|
| `GET /api/universes/spy` | Every position: ticker, name, sector, `asset_class`, weight (fraction, sums to 1.0), and all metric values (`null` = no data). ~53 KB gzipped |
| `GET /api/metrics` | Metric catalogue for the dropdowns: key, label, unit, scale, refresh — in display order |
| `GET /api/instruments/{ticker}` | Popup detail: P/E, market cap (USD), dividend yield and earnings yield (fractions). Finnhub, cached per ticker per day |
| `WS /api/live?ticker={ticker}` | Popup price feed: the latest bar immediately (last close when the market is shut), then each new minute bar as JSON `{"type": "bar", "ticker", "minute_utc", "open", "high", "low", "close", "volume"}`. Unknown ticker → closed with code `4404` |

Any ticker spelling works (`BRK.B`, `brk-b`, `BRK/B`). Alpaca's free tier allows one WebSocket connection, so every popup shares it through `LiveBarHub`: a ticker is subscribed upstream when its first popup opens and unsubscribed when the last one closes; the connection opens on demand, closes after 60s with no viewers, and reconnects (re-subscribing) if it drops.

Errors: `404` unknown universe/ticker; `503` provider down or rate-limited (with `Retry-After` when known). If a daily refresh fails, the previous snapshot keeps being served. CORS allows the Vite dev server (`http://localhost:5173`) by default; override with `CORS_ALLOWED_ORIGINS` in `.env`.

## Frontend

Vue 3 + TypeScript + Vite in `frontend/`. Needs Node 22.22+, 24.15+ or 26+ (developed on 26); npm comes with it.

```bash
cd frontend
npm install     # like `uv sync`: installs into frontend/node_modules
npm run dev     # http://localhost:5173, hot reload; API calls are proxied to :8000
```

Run the API server alongside it.

| Command | Does |
|---|---|
| `npm run test` | Vitest (watch mode locally, single run in CI) |
| `npm run type-check` | vue-tsc |
| `npm run lint` | Oxlint + ESLint (auto-fixes) |
| `npm run build` | Type-check + production build into `frontend/dist/` |
| `npm run gen:api` | Regenerate `src/api/schema.d.ts` from the backend's schema (no server needed; uses `uv`) |

Two views over one shared state, switchable without reloading data:

| View | What it shows | Interactions |
|---|---|---|
| **List** (built first) | One row per position: ticker, name, sector, weight, and a column per metric from `GET /metrics` | Sort by any column, filter (sector, text search), click a row → detail popup |
| **City** | Three.js treemap: sector districts, footprint = weight, height and colour = chosen metrics | Orbit, hover, click a building → detail popup |

- **One payload, two renderings.** Both views read the same `GET /universes/spy` response, and sorting and filtering happen in the browser (500 rows is trivial). No extra endpoints.
- **Filters are shared, sort is list-only.** A filter set in the list dims or hides the non-matching buildings in the city. Sorting only applies to the list, since city positions come from the treemap layout.
- **Same popup in both views.** Clicking loads fundamentals (`GET /instruments/{ticker}`) and opens the live price stream (`WS /live`). Rows never tick live; real-time stays popup-only.
- **List first** because it's quicker to build, tests the full data path (payload, formatting, popup, WebSocket) end-to-end, and gives a readable check on the numbers the city renders.

| Concern | Choice | Why |
|---|---|---|
| Framework | Vue 3 (Composition API) | Two views sharing state plus a table and a popup justify a framework. Vue's templates and `ref`/`computed` reactivity are close to Angular, and `watch()` suits updating an imperative Three.js scene |
| State | Pinia + URL | Two stores (universe, fundamentals) plus a live-bar composable; sort, filters, metric picks and the selected ticker live in the URL |
| Build | Vite + TypeScript | Fast dev server, typed API payloads |
| Table | TanStack Table v9 | Sorting and rendering with our own markup; filtering is a shared pure function |
| 3D | Three.js (`InstancedMesh`, `MapControls`) mounted in one Vue component | 500 buildings in one draw call |
| Layout | d3-hierarchy (squarified treemap) | Districts and footprints without custom packing |

Built out from the list view later: column picker, CSV export, portfolio columns (position P&L, contribution to return), selecting rows to highlight them in the city.

## Run with Docker

The production setup: one container where FastAPI serves both the API and the built frontend. Railway builds this same `Dockerfile` on every push to `main`. For day-to-day development use `npm run dev` + `uvicorn --reload` instead.

```bash
docker build -t stocktown .
docker run --rm -p 8000:8000 --env-file .env \
  -v stocktown-data:/data -e STOCKTOWN_DB_PATH=/data/stocktown.sqlite3 \
  stocktown
# http://localhost:8000
```

| Flag | Does |
|---|---|
| `--env-file .env` | Passes the API keys at run time; they are never inside the image |
| `-v stocktown-data:/data` + `STOCKTOWN_DB_PATH` | Keeps the stored snapshot across restarts (as the Railway volume does); without them each start rebuilds the city (~5s) |

## CLI

`uv run python -m stocktown <command>` runs the data previews.

| Command | Purpose |
|---|---|
| `holdings` | Print SPY constituents (top 10 by weight + JSON sample) |
| `bars [TICKERS...] [--days N]` | Historical daily bars from Alpaca |
| `fundamentals [TICKERS...]` | P/E, market cap, dividend yield from Finnhub |
| `stream [TICKERS...]` | Live minute bars via Alpaca WebSocket (market hours only). Uses Alpaca's single connection, so it fails with "connection limit exceeded" while the API server has a popup open |
| `verify` | Reconcile all SPY tickers against Alpaca's catalogue, check sector coverage, end-to-end sanity check |
| `metrics [TICKERS... \| --spy] [--metric KEY ...]` | Compute city metrics; `--spy` runs the full S&P 500 (~5s) |
| `openapi` | Print the API's OpenAPI schema as JSON (feeds the frontend's `npm run gen:api`) |

Defaults to `AAPL MSFT NVDA` when no tickers are given.

## Tests

```bash
uv run pytest
```

74 behavioural tests across metrics, services, providers and API routes, built from hand-written data with known answers — no network, ~0.7s. `tests/factories.py` holds test-data builders and fakes (loaders, clock); `tests/fake_alpaca.py` is an in-memory Alpaca stream. API tests run the real routes via FastAPI's `TestClient` with services swapped through `app.dependency_overrides`. Async tests use the anyio pytest plugin (`@pytest.mark.anyio`); `pytest-timeout` fails any test that hangs longer than 10s.

Each test guards a real failure mode (e.g. wrong one-year baseline, beta misaligned by date, five simultaneous visitors triggering five rebuilds, a closed popup leaking its subscription). Don't add tests that can't fail for a plausible bug — when adding tests, inject the bug they claim to catch and confirm they fail.

`TestClient` is not uvicorn: it cancels WebSocket handlers when the client leaves and reports close codes that a real server would turn into an HTTP 403. For WebSocket behaviour, also check against a real server.

Frontend: `cd frontend && npm run test` — 53 Vitest tests (stores, composables, components, whole-app routing) against a fake Api, same rules.

## Project layout

Organised in layers following the Spring-Boot-style separation of concerns: `domain` (types), `providers` (external integrations), `services` (business logic), `api` (HTTP), `cli` (dev-time entry). New layers (e.g. `persistence`) will be created the moment a concrete file needs to live in them, not before.

```
stocktown/
  __init__.py                        # public API re-exports (Holding, load_holdings, ...)
  __main__.py                        # `python -m stocktown` entry — delegates to cli.commands
  main.py                            # FastAPI app factory: middleware, error handlers, routers, warm-up
  config.py                          # .env loader → typed Settings (masked credentials), CORS origins
  exceptions.py                      # domain exceptions (unknown universe/ticker, upstream unavailable)

  domain/                            # Spring: entities / DTOs
    models.py                        # Holding, DailyBar, MinuteBar, Fundamentals, TradableAsset

  providers/                         # Spring: repositories / external integrations
    alpaca/
      client.py                      # shared httpx.Client factory (data + trading base URLs)
      prices.py                      # historical daily bars + latest minute bar (REST)
      stream.py                      # AlpacaBarConnection: one socket, subscriptions changeable live
      assets.py                      # tradable asset catalogue + ticker reconciliation
    finnhub/
      fundamentals.py                # P/E, market cap, dividend yield (batch rate-limited + single-ticker)
    ssga/
      spy_holdings.py                # SSGA fund holdings XLSX parser (any fund via fund_holdings_url)
      sectors.py                     # ticker → GICS sector from the 11 Select Sector SPDR funds

  services/                          # Spring: @Service — business logic over providers
    universes.py                     # UNIVERSES registry; SPY holdings + sectors + Alpaca symbols
    snapshot.py                      # SnapshotService: per-universe holdings + metrics, cached daily
    instruments.py                   # InstrumentService: popup fundamentals, cached per ticker per day
    assets.py                        # AssetCatalogue: resolves any ticker spelling to Alpaca's symbol
    live.py                          # LiveBarHub: shares Alpaca's single stream across all popups
    metrics/
      base.py                        # Metric ABC, Scale, Refresh, Unit
      market_data.py                 # lazy per-run data cache (one fetch for all metrics)
      price_series.py                # shared pure helpers (returns, windows, freshness)
      registry.py                    # ALL_METRICS, get_metric, compute_metrics
      <metric>.py                    # one file per metric

  api/                               # Spring: @RestController layer
    schemas.py                       # Pydantic response DTOs
    dependencies.py                  # singleton services for Depends() (overridable in tests)
    errors.py                        # domain exception → HTTP status (@ControllerAdvice)
    routes/
      universes.py                   # GET /universes/{id}
      metrics.py                     # GET /metrics
      instruments.py                 # GET /instruments/{ticker}
      live.py                        # WS /live?ticker=

  cli/
    commands.py                      # argparse dispatcher + preview functions

tests/                               # pytest, mirrors the package layout
  conftest.py                        # shared fixtures (anyio backend)
  factories.py                       # test-data builders + fakes (bars, loaders, clock)
  fake_alpaca.py                     # in-memory Alpaca stream for hub + route tests
  providers/test_*.py                # Alpaca stream message handling
  services/test_*.py                 # universes, snapshot, instruments, assets, live hub
  services/metrics/test_*.py         # one file per metric + registry contracts
  api/test_*_api.py                  # routes via TestClient
```

Each provider sub-package (`alpaca`, `finnhub`, `ssga`) re-exports its public functions from its `__init__.py`, so callers can write `from stocktown.providers.alpaca import load_daily_bars` without knowing the internal file. The top-level `stocktown/__init__.py` re-exports the whole public surface, so external code just needs `from stocktown import load_holdings, load_daily_bars, ...`.

### Where the remaining Spring layers will land

| Spring concept | When it appears | Where it goes |
|---|---|---|
| Interfaces (`PriceProvider`, `ReferenceProvider`) | When a second implementation justifies them | `stocktown/providers/interfaces.py` |
| `@Repository` / DB layer | After a working frontend — replaces the in-memory snapshot | `stocktown/persistence/` |

## Design notes

- **One module per external data source, uniform pipeline shape.** Each provider module exposes one public loader function that returns a typed dataclass or dict of dataclasses. Every module reads top-to-bottom as a pipeline of small, focused helpers.
- **Config is centralised.** `stocktown.config.get_settings()` is the only place that reads environment variables; every other module pulls typed credentials from there. Credentials dataclasses mask their values in `__repr__` to prevent accidental leaks via logs or debuggers.
- **Split-adjusted, not dividend-adjusted historical prices.** Matches what viewers expect from Yahoo Finance / TradingView (price return, not total return).
- **Ticker reconciliation via normalisation.** SPY file and Alpaca use slightly different punctuation for share classes (`BRK.B` vs `BRK/B`). Strip everything except letters and digits, uppercase, match. Current resolution rate: 100% of SPY tickers.
- **Real-time is popup-only, not full-city.** The city renders a static snapshot per session; live WebSocket streaming is used only for the detail view of a clicked-into stock. Sidesteps the free-tier subscription-limit unknown entirely.
- **Two views, one state.** The city and the list are renderings of the same data: the universe store plus URL state (filters, metric picks, selection). A new metric appears as a city dropdown option and a list column with no frontend change.
- **City metrics are price-only; fundamentals are click-only.** Alpaca bars are batched (fast at any universe size); Finnhub is one call per ticker per second. So P/E, market cap and dividend yield load in the detail popup when a stock is clicked, never for the whole city.
- **Metrics are per ticker, scaled per universe.** A metric never knows which universe a ticker came from. Raw values are stored; the frontend scales them against whatever city is on screen, so portfolios reuse every metric unchanged.
- **One payload per city.** `GET /universes/{id}` carries every position with every metric, so switching the height/colour metric needs no request. Items are `positions` with an `asset_class` so ETFs, options and commodities can join later without an API break.
- **Units are fractions everywhere.** Weights, returns and yields are all fractions (0.12 = 12%); the frontend formats them.

## Free-tier caveats

- Alpaca free tier uses the IEX feed, which is ~2-3% of US consolidated volume. Absolute volumes are meaningless; use ratios (e.g. today ÷ 20-day average) only.
- Finnhub free tier is capped at 60 requests/minute and US stocks only, with no bulk endpoint — which is why fundamentals are fetched per stock on click, not for the whole city.
- All providers' free terms can change without notice. Every module hides its provider behind a small function so the swap surface is minimal.
