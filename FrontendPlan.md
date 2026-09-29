# Frontend Implementation Plan

Ordered plan for the Vue 3 + Three.js frontend. Derived from the design grill in
the September 2026 session; assumes every decision in this document is settled
unless flagged as "TBD".

Companion docs: `StockTownOutline.md` (product/architecture), `CLAUDE.md`
(session context and working preferences), `README.md` (setup + CLI).

## How to use this document

- Phases are sequenced so every phase is independently reviewable, mergeable,
  and testable. No phase depends on later work compiling.
- Each phase lists **prerequisites** (what must be true before starting),
  **deliverables** (what changes when it's done), **done-when** (the objective
  bar), and **checkpoints** (natural "wait for review" pauses inside the phase).
- The user reviews all code before it is written. Every code-producing
  checkpoint is a hand-off: proposed code goes in chat, explicit approval before
  `Write`/`Edit`.

## Global decisions carried into every phase

Full reasoning lives in the grill transcript; this is a reference card.

| Area | Decision |
|---|---|
| Location | `frontend/` at repo root |
| Scaffold | `create-vue` with TypeScript, Router, Pinia, Vitest, ESLint, Prettier (no JSX, no E2E yet) |
| Package manager | npm |
| TypeScript | `strict: true` + `noUncheckedIndexedAccess: true` |
| Linter/formatter | ESLint + Prettier (create-vue defaults) |
| Folder shape | Type-based: `api/`, `components/`, `composables/`, `lib/` (helpers: shadcn `cn`, formatters), `stores/`, `types/`, `views/`, `router/` |
| HTTP client | `openapi-fetch` |
| Types (HTTP) | Generated from `/openapi.json` via `openapi-typescript` → `src/api/schema.d.ts` |
| Types (WS) | Hand-written discriminated union in `src/api/live.ts` (OpenAPI doesn't cover WS) |
| Popup | Nested route (`/:universeId/list/ticker/:ticker`, `/:universeId/city/ticker/:ticker`), right-side drawer |
| URL state | View, ticker, sort, filters, metric picks — all live in URL |
| Styling | Tailwind CSS + shadcn-vue |
| Theme | Zinc neutral + teal primary (avoids RdBu and plasma's purple end); Inter self-hosted via `@fontsource-variable/inter` |
| Dev integration | Vite proxy to FastAPI |
| API paths | Everything under `/api` (REST + `WS /api/live`); page routes own the rest; plan text omits the prefix |
| Pinia | Three Setup Stores: `useUniverseStore`, `useFundamentalsStore`, `useLiveBarStore` |
| WS consumption | `useLiveBar(ticker)` composable + 3-try exponential-backoff reconnect |
| Testing | Vitest + `@testing-library/vue`; behavioural names; inject fakes; mutation-verify |
| CI | GitHub Actions — one workflow, backend job + frontend job |
| Prod serving | Deferred until deployment. Likely FastAPI serving `frontend/dist` (same-origin), with a fallback to `index.html` for deep links |
| List | All columns visible + TanStack Table + TanStack Virtual + single-column sort |
| List filters | Sector multi-select chips + ticker/name substring; no metric range filters |
| URL params | `?sort=-beta_1y&sector=Technology,Financials&q=aapl&height=one_year_return&color=day_change` |
| Popup layout | Right-side drawer, stacked sections (header / metrics / fundamentals / live) |
| Loading UX | `<Suspense>` for boot; manual `{loading, error, data}` refs per store thereafter |
| Formatting | `src/lib/format.ts`, `Intl.NumberFormat('en-US', …)`, driven by `metric.unit` |
| City layout | Meta-treemap of treemaps (sector districts → holdings) with padding for streets |
| City rendering | Single `InstancedMesh` of `BoxGeometry(1,1,1)`, per-instance matrix + colour |
| City camera | `MapControls`, perspective @ ~45°, polar clamp `[15°, 75°]` |
| City palettes | Plasma (sequential), RdBu clipped `[0.1, 0.9]` (diverging, driven by new `signed` flag) |
| City hover/select | Coloured outline + 1.05× scale; selected uses thicker outline in accent |

## Universe-agnostic by design

The UI renders *a universe* — `{id, name, session_date, positions[]}` — and
never assumes it is the S&P 500. Adding an index fund = one backend
`UNIVERSES` entry, no UI change. Portfolio import later = another source of
the same shape.

Rules (cheap now, expensive to retrofit):

- **Universe id lives in the URL:** `/:universeId/list`, `/:universeId/city`,
  `/:universeId/list/ticker/:ticker`. `/` redirects to the default. The only
  `"spy"` literal in the frontend is `DEFAULT_UNIVERSE_ID` in one constants file.
- **Store takes the id:** `load(universeId)`. Page title and date come from the
  payload's `name` and `session_date`, never hard-coded text.
- **Nothing counts sectors or assumes they exist:** districts, filter chips and
  legends derive from the distinct sectors in the payload; `sector: null`
  groups under "Unclassified".
- **Nothing assumes equities:** `asset_class` is displayed, not assumed; popup
  sections whose data is missing (e.g. no fundamentals for an ETF) show
  "unavailable" rather than breaking.
- **Columns and metric pickers come from `GET /metrics`** (already the case).
- **Tests use a small non-SPY fixture:** e.g. a 3-position "Test Portfolio"
  with one `sector: null` and one non-equity position, so any hidden SPY
  assumption fails a test.

Deliberately *not* built yet (no second universe to justify them):
- A universe picker and `GET /universes` list endpoint. Added with the second
  universe; the picker is then one dropdown bound to the route param.
- Portfolio import. Needs a backend endpoint that computes metrics for an
  arbitrary ticker list (the metric layer is already per-ticker).

## Backend follow-ups (small; queued alongside frontend work)

- **Add `signed: bool` to `Metric` class** and to `MetricInfoResponse` in
  `stocktown/api/schemas.py`. Populate per metric (`day_change`,
  `one_year_return` → `True`; others → `False`). Regenerate frontend types
  afterwards (`npm run gen:api`).
- **Confirm Finnhub dividend-yield unit** (fraction vs percent) when wiring the
  popup fundamentals section. Update `src/lib/format.ts` usage accordingly.
- **Make `unit`, `scale`, `refresh` `Literal` types** in
  `MetricInfoResponse`, so the generated TypeScript gets `'percent' | 'ratio'`
  instead of `string` (lets `formatByUnit` take the schema type directly).
- **Add `last_close` to `PositionResponse`** — the drawer's live day change
  needs the previous close, and the payload currently carries no price.
  Lands in the same `gen:api` regeneration as `signed`.

All land as separate small commits before Phase 6.

---

## Phase 0 — Scaffolding & CI foundation

Goal: an empty-but-configured `frontend/` that boots to a blank page, plus CI
running both backend and frontend on every push.

**Prerequisites:** none.

**Deliverables:**

- `frontend/` directory with `create-vue` output (TypeScript, Router, Pinia,
  Vitest, ESLint, Prettier; no JSX, no E2E)
- `frontend/tsconfig.json` sets `strict: true` and `noUncheckedIndexedAccess: true`
- `frontend/vite.config.ts` proxies `/api` (HTTP + WebSocket) to
  `http://localhost:8000`
- Tailwind CSS v4 installed (`tailwindcss`, `@tailwindcss/vite`) as a Vite
  plugin — no `postcss`/`autoprefixer`/`tailwind.config.js`; the theme
  (`zinc` neutral + teal primary) lives in `src/assets/main.css`
- shadcn-vue 2.8 initialised via its CLI (`--base reka --style vega
  --icon-library lucide -b zinc`); components land in `src/components/ui/`
  under our own source control. `slate` no longer exists and `mist` emits no
  CSS variables (build fails), hence `zinc`. The Google Fonts `@import` it
  writes is replaced by the self-hosted font.
- Dependencies added:
  - `openapi-fetch`, `openapi-typescript` (dev). `openapi-typescript` 7.13
    declares `typescript@^5` as a peer; `package.json` `overrides` points it
    at the project's TypeScript 6 (verified: generated schema passes
    `tsc --strict`). Remove the override once upstream supports TS 6. (`skipLibCheck` is on, so the schema file itself is only checked through `client.ts` using its types.)
  - `@tanstack/vue-table`, `@tanstack/vue-virtual`
  - `d3-hierarchy`, `d3-scale`, `d3-scale-chromatic` (+ their `@types/*`)
  - `three`, `@types/three`
  - `@testing-library/vue` (dev)
- `frontend/package.json` scripts: `dev`, `build`, `preview`, `type-check`,
  `lint`, `test`, `gen:api` (regenerates `src/api/schema.d.ts` from the
  backend schema via `python -m stocktown openapi`; no server needed)
- `.github/workflows/ci.yml` with two jobs:
  - **backend**: `uv sync`, `uv run pytest`
  - **frontend**: `npm ci`, `npm run lint && git diff --exit-code` (lint
    auto-fixes, so fail if it changed anything), `npm run test`,
    `npm run build` (includes type-check)
  - The schema drift check (`gen:api` + `git diff`) moves to Phase 1, once
    `schema.d.ts` exists
- ~~`stocktown/main.py` static mount~~ — deferred until deployment (dev uses
  the Vite server; see "Prod serving")
- `README.md` gets a `## Frontend` section: install, dev, build steps
- `.gitignore`: no change needed — create-vue's `frontend/.gitignore` covers
  `node_modules`, `dist`, `coverage`

**Done when:**

- `npm run dev` inside `frontend/` serves the create-vue default page at
  `http://localhost:5173`
- `npm run type-check`, `npm run lint`, `npm run test` all pass on the empty
  project
- `npm run gen:api` writes `src/api/schema.d.ts`
- A push triggers CI; both jobs go green

**Checkpoints (review pauses):**

1. Full list of `npm install` commands + final `package.json` — before install
2. `tsconfig.json`, `vite.config.ts`, Tailwind CSS setup, shadcn `components.json`
3. `ci.yml` (both jobs)
4. Post-run: verify the "done when" checks

---

## Phase 1 — Contract wire-up

Goal: a typed HTTP client and typed WS message layer, ready to be consumed by
stores. No UI yet.

**Prerequisites:** Phase 0 complete. No running backend needed.

**Deliverables:**

- `python -m stocktown openapi` — prints the schema straight from the app;
  `npm run gen:api` pipes it into `openapi-typescript`
- `src/api/schema.d.ts` — generated, committed, excluded from Prettier
  (`.prettierignore`)
- CI: schema drift check — `npm run gen:api && git diff --exit-code
  src/api/schema.d.ts` (frontend job installs `uv` for this)
- `src/api/client.ts` — `Api` interface (`fetchUniverse`, `fetchMetrics`,
  `fetchInstrument`) + `createApi({ baseUrl, fetch })` built on
  `openapi-fetch`. Stores depend on `Api`, so tests pass a plain fake.
  Errors throw `ApiError { status, retryAfterSeconds }`. Base URL blank
  (relative paths, dev proxy handles it).
- `src/api/live.ts` — hand-written WS message types:
  ```ts
  export interface LiveBar {
    type: 'bar'; ticker: string; minute_utc: string
    open: number; high: number; low: number; close: number; volume: number
  }
  export type LiveMessage = LiveBar // future: | LiveStatus
  ```
  Plus `parseLiveMessage(raw: string): LiveMessage` — trusts our server for
  the fields, throws on unknown `type` (fail loud).
- `src/__tests__/fixtures.ts` — `TEST_PORTFOLIO`, the non-SPY fixture (see
  "Universe-agnostic by design")
- create-vue example code removed; `App.vue` is a bare `<RouterView />`
- `src/types/` (`SortSpec`, `FilterSpec`, `MetricSelection`) moved to Phase 3,
  next to their first consumer

**Done when:**

- `client.spec.ts` and `live.spec.ts` pass and are mutation-verified
- `npm run gen:api` leaves `schema.d.ts` unchanged
- No runtime code depends on `any`

**Checkpoints:**

1. `client.ts`, `live.ts`, tests and the `gen:api` pipeline — one proposal,
   prototyped in scratch first

---

## Phase 2 — Stores & the live composable

Goal: all data-fetching primitives in place, unit-tested, no UI consumers yet.

**Prerequisites:** Phase 1 complete.

**Deliverables:**

- `src/stores/universe.ts` — `useUniverseStore` (Setup Store). Accepts an
  injected client for testability. Exposes `positions`, `sectors`,
  `metricsCatalogue` (from `/metrics`), plus `{loading, error}`. Method:
  `load(universeId)` fetches `/universes/{universeId}` and `/metrics` in parallel.
- `src/stores/fundamentals.ts` — `useFundamentalsStore`. Per-ticker cache
  keyed by ticker; `get(ticker)` returns cached entry or fetches from
  `/instruments/{ticker}`. Entry shape: `{loading, error, data}` per ticker.
- `src/stores/liveBar.ts` — `useLiveBarStore`. Per-ticker latest-bar cache.
  Written to by `useLiveBar` composable (below); read by drawer components.
- `src/composables/useLiveBar.ts` — takes a `Ref<string>` ticker; opens WS on
  mount, closes on unmount, writes bars into `useLiveBarStore`. Handles WS
  close codes: `4404` (unknown ticker) surfaces as an error ref; `4503`
  (provider unavailable) surfaces separately. 3-try exponential backoff on
  unexpected close (`1s → 2s → 4s`), then gives up and exposes a `disconnected`
  status. Ref-safe: switching ticker mid-life closes the old WS and opens the
  new one.
- `src/api/liveClient.ts` — thin wrapper around browser `WebSocket` that the
  composable uses; extracted so tests can inject a fake WS.

**Tests (mirror backend rules):**

- `universe.spec.ts` — inject fake client; assert `load()` transitions
  `{loading:true} → data → {loading:false}`; assert error path when client throws.
- `fundamentals.spec.ts` — inject fake client; assert cache hit on second `get`;
  assert per-ticker error isolation.
- `liveBar.spec.ts` + `useLiveBar.spec.ts` — inject fake WS; assert bar arrival
  updates store; assert reconnect fires 3× on unexpected close, then gives up;
  assert unmount closes cleanly.

Behavioural test names. Hand-built payloads via `src/__tests__/fixtures.ts` (mirror
backend's `tests/factories.py`). No `vi.mock`; inject fakes as constructor
args.

**Done when:**

- All store + composable tests pass with `npm run test`
- Coverage for each store's public methods (not for coverage's sake — every
  test must be able to catch a plausible bug; mutation-verify the reconnect
  logic and the cache hit)
- `type-check` passes

**Checkpoints:**

1. `universe.ts` + its tests
2. `fundamentals.ts` + its tests
3. `liveBar.ts` + `useLiveBar.ts` + `liveClient.ts` + their tests
4. Mutation verification report on the reconnect logic (inject a bug, confirm a
   test fails)

---

## Phase 3 — Routing, shell, formatters

Goal: the app boots into a working shell with routing, a drawer slot, and
number formatting — but the list is still a placeholder.

**Prerequisites:** Phase 2 complete.

**Deliverables:**

- `src/router/index.ts` — routes:
  - `/` → redirect to `/spy/list` (`DEFAULT_UNIVERSE_ID`)
  - `/:universeId/list` (name `list`, component: `ListView`)
  - `/:universeId/list/ticker/:ticker` (name `list-ticker`, component:
    `ListView`, drawer slot receives ticker)
  - `/:universeId/city` (name `city`, component: `CityView`)
  - `/:universeId/city/ticker/:ticker` (name `city-ticker`, component:
    `CityView`, drawer slot receives ticker)
- `src/App.vue` — top-level layout: header (app title, view switcher), main
  content slot (router-view), drawer slot (router-view name="drawer"). Wraps
  the main router-view in `<Suspense>` for boot fetch. Suspense fallback: a
  full-screen skeleton (shadcn Skeleton).
- `src/composables/useBootFetch.ts` — awaited in async setup of a top-level
  wrapper component; calls `useUniverseStore().load(route.params.universeId)`. Suspense hooks off this.
- `src/composables/useQuerySort.ts`, `useQueryFilters.ts`, `useQueryMetrics.ts`
  — read/write URL query params for sort, filters, and metric picks. Return
  typed refs. Two-way sync with `useRoute`/`useRouter`.
- `src/types/` (moved from Phase 1) — `SortSpec`, `FilterSpec`,
  `MetricSelection` (which metric drives height/colour), written alongside
  the composables above. Every field justified by a consumer.
- `src/lib/format.ts` — pure functions:
  - `formatPercent(x: number, digits = 1)` → `"12.3%"`
  - `formatSignedPercent(x: number, digits = 1)` → `"+1.2%"` / `"−0.4%"`
    (uses U+2212 minus, not hyphen, for typographic correctness)
  - `formatRatio(x: number, digits = 2)` → `"1.05×"`
  - `formatCompactMoney(x: number)` → `"$1.2B"` (uses `Intl.NumberFormat`
    with `notation: "compact"`)
  - `formatByUnit(unit: "percent" | "ratio", value: number | null, opts?)` —
    dispatch by metric unit, returns `"—"` for `null`
- `src/lib/__tests__/format.spec.ts` — behavioural tests for each formatter, edge cases
  (0, negative, null, very large, very small).

**Done when:**

- App boots, shows a header + placeholder list/city view + no drawer
- Navigating to `/spy/list/ticker/AAPL` re-enters `ListView` with drawer route
  populated (drawer content is still a placeholder)
- Sort/filter/metric composables round-trip through the URL — updating a ref
  updates the URL, and pasting a URL populates the refs
- All formatter tests pass; mutation-verify the sign handling on
  `formatSignedPercent`

**Checkpoints:**

1. Route table + `App.vue` shell
2. URL-sync composables + tests
3. `format.ts` + tests
4. Live in browser: boot, deeplink, view-switch all work

---

## Phase 4 — List view

Goal: the working list, backed by the store, with sort/filter/URL sync and a
row-click that opens a placeholder drawer route.

**Prerequisites:** Phase 3 complete.

**Deliverables:**

- `src/views/ListView.vue` — hosts the table + filter bar + drawer outlet
- `src/components/list/FilterBar.vue` — sector multi-select chips (shadcn
  Toggle group) + ticker/name search input (shadcn Input, debounced ~200ms).
  Reads/writes URL via `useQueryFilters`.
- `src/components/list/PositionsTable.vue` — TanStack Table + TanStack Virtual:
  - Columns: ticker, name, sector, weight, then one column per metric
    (definitions pulled from `useUniverseStore().metricsCatalogue`)
  - Single-column sort, driven by `useQuerySort`
  - Filters applied before sort (composable — a plain function over positions)
  - Row click → `router.push({ name: 'list-ticker', params: { universeId, ticker }, query: route.query })`
    (query preserved so sort/filter survive drawer navigation)
  - Cells: `<MetricCell :value :unit>` — dispatches to `formatByUnit`; null
    shows `—`
- `src/components/list/MetricCell.vue` — single-line, right-aligned for
  numbers, `tabular-nums` for column alignment
- Row highlight when its ticker is the selected drawer route
- Tests:
  - `PositionsTable.spec.ts` — behavioural: sorting by beta desc puts highest
    beta first; searching "AAP" narrows to matching tickers; clicking a row
    pushes the expected route (real router with memory history).
  - `FilterBar.spec.ts` — sector chip toggles URL param; search input debounces.
  - Fixtures live in `src/__tests__/fixtures.ts` — hand-built `Position` records with
    known metric values.

**Done when:**

- Browser: `/spy/list` shows all 500 rows, sort works, filter works, row-click
  navigates to `/spy/list/ticker/AAPL` (drawer still placeholder)
- Refreshing on `/spy/list/ticker/AAPL?sort=-beta_1y&sector=Technology` preserves
  everything
- Virtualised scroll stays smooth (visually verify — no jank at 500 rows)
- All list-related tests pass
- Contract: the columns rendered exactly match `/metrics` output — if the
  backend adds a metric, this table shows it without code changes

**Checkpoints:**

1. `PositionsTable.vue` — TanStack setup, column defs, sort wiring
2. `FilterBar.vue`
3. Row-click + selection highlighting
4. Tests
5. Manual browser check

---

## Phase 5 — Popup (drawer)

Goal: clicking a row opens a working drawer with live-updating price, city
metrics, fundamentals, and OHLCV. Same drawer will serve the city view later.

**Prerequisites:** Phase 4 complete.

**Deliverables:**

- `src/components/drawer/TickerDrawer.vue` — shadcn Sheet, right side. Opens
  when the current route has `:ticker`; closing pushes back to the parent
  (`/:universeId/list` or `/:universeId/city`). Internal layout is a scrollable column of sections.
- `src/components/drawer/DrawerHeader.vue` — ticker, name, sector, live price,
  day change. Live price + day change from `useLiveBar(ticker)`. Day change
  computed against the position's `last_close` from `useUniverseStore`
  (already in memory once the `last_close` backend follow-up lands).
- `src/components/drawer/CityMetricsSection.vue` — compact 2-column list of
  every metric with its formatted value. Read from `useUniverseStore`.
- `src/components/drawer/FundamentalsSection.vue` — P/E, market cap, dividend
  yield. Uses `useFundamentalsStore().get(ticker)`. Skeleton while loading;
  "unavailable — [retry]" on error.
- `src/components/drawer/LiveBarSection.vue` — latest bar OHLCV + timestamp.
  Uses `useLiveBar(ticker)`. Shows "connecting…" until first message;
  "disconnected — retrying" on backoff; final "disconnected" after backoff
  exhausted.
- Status handling:
  - WS 4404: replace drawer body with "ticker not found"
  - WS 4503: amber pill "market data provider unavailable"
  - Fundamentals 404: "no fundamentals for this ticker" (fine; not every ticker has them)
  - Fundamentals 503 with `Retry-After`: parse header, retry once after that delay
- Tests:
  - `TickerDrawer.spec.ts` — mounts open with `:ticker`; closes → back-nav;
    unknown-ticker path.
  - `LiveBarSection.spec.ts` — inject fake WS; assert render before/after first
    bar; assert reconnect status transitions.
  - `FundamentalsSection.spec.ts` — inject fake client; loading → data → error
    paths.

**Done when:**

- Clicking a row on `/spy/list` opens the drawer with the header populated
  immediately (data already in the snapshot)
- Fundamentals section shows skeleton, then real values within ~1s
- Live bar section shows "connecting…" for a fraction of a second, then bars
  arrive and update
- Closing the drawer returns to `/spy/list` with sort/filter intact
- All drawer tests pass; mutation-verify the reconnect UI transitions

**Checkpoints:**

1. `TickerDrawer.vue` shell + open/close logic + selection highlight coordination
2. Each section component (one PR each is fine)
3. Error/status handling
4. Tests
5. Manual browser check with the backend live

---

## Phase 6 — City view

Goal: the treemap-city renders, responds to metric dropdowns, and clicking a
building opens the same drawer as the list.

**Prerequisites:** Phase 5 complete. Backend `signed: bool` follow-up merged
and `npm run gen:api` re-run. Finnhub dividend-yield unit verified.

**Deliverables:**

- `src/views/CityView.vue` — hosts the metric dropdowns + canvas + legend +
  drawer outlet
- `src/components/city/MetricPickers.vue` — two shadcn Select components:
  "Height" and "Colour". Options from `useUniverseStore().metricsCatalogue`.
  Reads/writes URL via `useQueryMetrics`.
- `src/composables/useCityLayout.ts` — pure function turning positions +
  sector aggregates into `BuildingLayout[]`. Uses `d3.hierarchy` +
  `d3.treemap` twice:
  - Outer treemap: one district per distinct sector in the payload
    (null → Unclassified), sized by aggregate weight; `paddingOuter` wide
    (avenue-like gaps between districts)
  - Inner treemap per sector: holdings sized by weight; `paddingInner` narrow
    (street-like gaps between buildings)
  - Output: `{ ticker, x, z, width, depth, sector }` per building
- `src/components/city/CityCanvas.vue` — imperative Three.js scene held in one
  component. Life-cycle:
  - `onMounted`: create renderer (`WebGLRenderer` with antialias + soft
    shadows), scene, `PerspectiveCamera`, `MapControls` with polar clamps
    `[15°, 75°]`, `AmbientLight` + `DirectionalLight` (angled from
    above-left, `shadow.mapSize = 2048`), ground `Mesh` (grey plane,
    receives shadows), and one `InstancedMesh` of `BoxGeometry(1,1,1)`
    with `MeshStandardMaterial` (`vertexColors` + per-instance colour
    attribute)
  - `watch`: on layout change / metric change / theme change, rebuild the
    instance matrices and colour buffer, flip `needsUpdate` flags
  - `onUnmounted`: dispose geometries, materials, renderer, `MapControls`;
    cancel `requestAnimationFrame`
  - Frame loop: `MapControls.update()` + `renderer.render()`; only runs when
    the camera moves or `needsUpdate` is set (invalidate-on-change, not fixed
    60fps)
- `src/composables/useCityColour.ts` — pure: given metric + `signed` flag +
  value + domain, returns a Three colour. Uses `d3.interpolatePlasma` for
  sequential; `d3.interpolateRdBu` clipped `[0.1, 0.9]` and centred on 0 for
  diverging; nulls → neutral grey.
- `src/composables/useCityHeight.ts` — pure: given metric + `scale` hint +
  value + domain, returns a height in world units. `d3.scaleLinear` /
  `scaleLog` / `scaleQuantile` mapped to `[1, 20]`. Log scale guards against
  non-positive inputs (falls back to linear for that metric).
- `src/components/city/SectorLabels.vue` — `CSS2DRenderer` overlay; one HTML
  label per sector positioned above the district centroid, billboarded
  automatically because it's DOM.
- `src/components/city/BuildingTooltip.vue` — screen-space HTML tooltip
  anchored to hovered building. Shows ticker, name, current height-metric
  value. Hidden when nothing hovered.
- `src/components/city/Legend.vue` — fixed corner overlay; renders the current
  colour palette as a gradient with min / mid / max labels. Sequential shows
  `[min, max]`; diverging shows `[−max, 0, +max]`.
- Interaction:
  - Hover: `Raycaster` on `pointermove` (throttled to `requestAnimationFrame`);
    hovered instance gets an outline (via a second slightly-larger
    `InstancedMesh` in accent colour, only the hovered index visible) + 1.05×
    scale
  - Click: push `{ name: 'city-ticker', params: { universeId, ticker } }` with query preserved
  - Selection (route ticker exists): thicker outline in accent colour on the
    selected building
- Tests (Vitest — no browser needed for the pure bits):
  - `useCityLayout.spec.ts` — hand-built positions; assert total footprint
    equals total area minus padding; assert sector districts are correctly
    scoped.
  - `useCityColour.spec.ts` — assert 0 maps to palette midpoint (diverging);
    assert null returns grey.
  - `useCityHeight.spec.ts` — assert domain edges map to `[1, 20]`; log
    fallback fires on non-positive input.
  - No component tests for `CityCanvas` — Three.js in JSDOM is a losing battle;
    manually verify in browser instead.

**Done when:**

- Browser: `/spy/city` renders the treemap-city with plasma-coloured buildings on
  a light ground with visible street corridors
- Both dropdowns work; URL updates on change; refreshing preserves selections
- Hover shows outline + tooltip; click opens the drawer at
  `/spy/city/ticker/AAPL`; drawer close returns to `/spy/city` with same metric picks
- Rotating/panning/zooming feels smooth; camera cannot clip below the ground
  plane or flip upside down
- Legend matches the current colour metric; changes with the dropdown
- All city-related pure-function tests pass

**Checkpoints:**

1. `useCityLayout` + `useCityHeight` + `useCityColour` (all pure, testable in
   isolation) — write and test these before touching Three.js
2. `CityCanvas.vue` skeleton: scene, camera, controls, ground, one instanced
   box for every position with fixed height/colour. Verify it renders and
   controls feel right.
3. Wire metric dropdowns and colour/height scales; verify updates
4. Hover outline + tooltip
5. Click → drawer wiring
6. Sector labels + legend
7. Manual browser check on full S&P

---

## Phase 7 — Polish, accessibility, follow-throughs

Goal: things a real user would notice, but that don't gate the earlier phases.

**Prerequisites:** Phase 6 complete.

**Deliverables:**

- Global toast system (shadcn Toast) for `Retry-After`-driven snapshot retries
  and one-off errors
- Keyboard nav pass:
  - Drawer: `Esc` closes; focus trapped while open; focus returns to the
    triggering row/building on close (shadcn Sheet handles most of this;
    verify)
  - Table: `Tab` moves through header sort buttons and filter chips; row focus
    with `Tab`; `Enter` opens drawer
- Screen-reader pass on the drawer (sensible headings, `aria-live` on live
  price)
- Loading skeletons anywhere still showing bare spinners
- Empty-state components (0 filtered results in list; ticker not in universe on
  direct drawer link)
- README updates: dev workflow, `gen:api` step, how to run tests, prod build
- Confirm Finnhub dividend-yield unit and adjust `format.ts` usage
- Delete any scratch/scaffold code left over from Phases 0–6

**Done when:**

- Keyboard-only navigation reaches every interactive control in list + drawer
- Toasts fire on 503s
- README explains a full local loop start-to-finish

**Checkpoints:**

1. Toast wiring + retry integration
2. Keyboard pass
3. README

---

## What's explicitly not in this plan

Called out so future-me doesn't wonder whether they were forgotten:

- **E2E tests (Playwright).** Deferred until the list view is stable and worth
  driving end-to-end. Adding it later is `npm init playwright` + one
  workflow job.
- **Column picker on the list.** All columns visible for MVP.
- **CSV export from the list.** Roadmap item.
- **Portfolio-import mode.** Roadmap item. The UI is built to accept it — see
  "Universe-agnostic by design".
- **Persistence layer (SQLite).** Deliberately after the frontend, per
  `CLAUDE.md`.
- **Cross-metric filters (range sliders).** Sorting covers the "show me the
  extremes" use case.
- **Roads as relationship overlays.** Corridors are reserved in the layout,
  but nothing draws in them yet. Real design work will happen when the
  underlying relationship data exists.
- **Live city.** Popup-only realtime remains the design; the city itself is a
  per-session snapshot.
- **Windows / roof detail on buildings.** Flat-topped boxes.
- **LOD in the city.** 500 buildings render fine as-is; revisit only if
  profiling says otherwise.
- **Runtime WS message validation (zod/valibot).** Type alias is enough for an
  internal contract with a tiny surface.
- **Auto-locale detection.** `en-US` hardcoded; revisit if the app ever ships
  to non-US audiences.

## Sequencing rationale (short)

- Phase 0 first because CI catches regressions from the very first frontend
  commit; deferring CI is how projects end up without it.
- Phase 1 before any UI because generated types force the rest of the code to
  match the backend from day one.
- Phase 2 (stores) before Phase 3 (routing) because the shell's Suspense
  fallback needs a real async operation to await.
- Phase 4 (list) before Phase 5 (popup) because the list is faster to build,
  verifies the data path end-to-end, and its row-click is the first thing that
  needs a drawer route.
- Phase 5 (popup) before Phase 6 (city) because the drawer is shared between
  both views — building it once against the simpler view catches contract
  issues cheaply.
- Phase 6 (city) last because Three.js is the biggest unknown for a Vue-new
  developer, and it benefits from the other views being green so problems
  isolate to the canvas.
- Phase 7 after everything because polish landing before the substance risks
  polishing code that gets rewritten.
