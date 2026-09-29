# Frontend Implementation Plan

Phased plan for the Vue 3 + Three.js frontend. Phases 0–4 are done and
summarised as they now stand; Phases 5–7 are the remaining work.

Companion docs: `CLAUDE.md` (session context, working preferences — wins if
anything here disagrees), `README.md` (setup, commands), `StockTownOutline.md`
(product vision).

## How to use this document

- Each remaining phase lists **prerequisites**, **deliverables**, **tests**,
  **done-when** and **checkpoints** (review pauses).
- Every code-producing checkpoint: prototype in scratch, mutation-check the
  tests, present the code in chat, write only after explicit approval. UI is
  confirmed by the user in their own browser against a short checklist.
- When a phase finishes, collapse it into a short "done" summary below —
  keep what exists and why, drop the history.

## Global decisions

| Area | Decision |
|---|---|
| Location / tooling | `frontend/`, `create-vue` (TypeScript, Router, Pinia, Vitest, ESLint + Oxlint, Prettier), npm, Node 22.22+/24.15+/26 |
| TypeScript | `strict` + `noUncheckedIndexedAccess` |
| Folder shape | `api/` (client, generated schema, WS types), `components/`, `composables/` (`use*` functions that use Vue reactivity or inject), `lib/` (pure functions: formatters, filtering, city maths, shadcn `cn`), `stores/`, `views/`, `router/`. Types live next to the function that uses them |
| API paths | Everything under `/api` (REST + `WS /api/live`); page routes own the rest. Plan text omits the prefix |
| HTTP | `openapi-fetch` behind a small `Api` interface (`src/api/client.ts`); types generated from the backend by `npm run gen:api`; CI fails if they drift |
| WS | Hand-written `LiveBar` type + `parseLiveMessage` (`src/api/live.ts`) |
| DI | `app.provide(API_KEY, createApi())`; stores call `useApi()`. Tests provide fakes |
| State | Pinia: `useUniverseStore`, `useFundamentalsStore`. Live feed: `useLiveBar` composable owned by the drawer. Everything shareable (view, ticker, sort, filters, metric picks) lives in the URL |
| URL | `/:universeId/list[/ticker/:ticker]`, `/:universeId/city[/ticker/:ticker]`; query `?sort=-beta_1y&sector=Technology&sector=Financials&q=aapl&cols=beta_1y&height=one_year_return&color=day_change` |
| Loading UX | Layout watches the URL's universe id and calls `store.load`; skeleton + "Building today's snapshot…" while loading; per-store `{loading, error}` thereafter. No `<Suspense>` (experimental) |
| List | TanStack Table v9 for sorting + rendering; metric columns chosen with a column picker (`?cols=`; default 1-year return + day change, so the table fits the screen — the drawer shows every metric, and serves the city too); filtering is the shared pure `filterPositions`; single-column sort; no pagination; virtual scrolling only if a real portfolio needs it; grouping by asset class via v9 later |
| List filters | Sector chips + ticker/name search; no metric range filters |
| Styling | Tailwind v4 + shadcn-vue (`vega`, zinc neutral, teal primary, self-hosted Inter). Plain Tailwind markup until a shadcn component earns its place (the drawer's Sheet, the column picker's DropdownMenu). `shadcn-vue add` inserts a Google Fonts `@import` into `main.css` each time — delete it (Inter is self-hosted) |
| Formatting | `src/lib/format.ts` (`Intl.NumberFormat('en-US')`, typographic minus), driven by `metric.unit` |
| Popup | Right-side drawer, nested child route of each view; sections: header / city metrics / fundamentals / live |
| City | Treemap of treemaps (sector districts → holdings, padding = streets); one `InstancedMesh` of unit boxes; `MapControls`, polar clamp `[15°, 75°]`; palettes plasma (sequential) and RdBu clipped `[0.1, 0.9]` (diverging, from the `signed` flag); hover/select outline. Route lazy-loaded so list-only visits never download Three.js |
| Testing | Vitest + Testing Library; behavioural names; fakes injected, no `vi.mock`; every test mutation-verified; non-SPY fixture (`TEST_PORTFOLIO`) |
| CI | One workflow: backend (uv, pytest) + frontend (schema drift, lint, Prettier, tests, build) |
| Prod serving | Deferred until deployment; likely FastAPI serving `frontend/dist` same-origin with an `index.html` fallback for deep links |

## Universe-agnostic by design

The UI renders *a universe* — `{id, name, session_date, positions[]}` — and
never assumes it is the S&P 500. Adding an index fund = one backend
`UNIVERSES` entry, no UI change. Portfolio import later = another source of
the same shape.

- The universe id lives in the URL; the only `"spy"` literal is
  `DEFAULT_UNIVERSE_ID` in `src/router/index.ts`.
- Titles and dates come from the payload (`name`, `session_date`).
- Sectors are derived from the payload; `sector: null` → "Unclassified".
- Nothing assumes equities: `asset_class` is displayed, not assumed; missing
  popup data shows "unavailable".
- Columns and metric pickers come from `GET /metrics`.
- Tests use `TEST_PORTFOLIO` (an unclassified position, a non-equity one), so
  a hidden SPY assumption fails a test.

Not built until a second universe exists: a universe picker +
`GET /universes`; protection against two universe loads racing; keeping the
current universe on screen when a *reload* fails (the store already does,
the layout still swaps in the error page). Portfolio import needs a backend
endpoint that computes metrics for an arbitrary ticker list.

---

## Done: Phases 0–4

**Phase 0 — Scaffold and CI.** `create-vue` app; Tailwind v4 via
`@tailwindcss/vite` (theme in `src/assets/main.css`); shadcn-vue initialised
(`components.json`, `src/lib/utils.ts`; `slate` no longer exists and `mist`
breaks the build, hence `zinc`); Vite proxies `/api` (HTTP + WS) to `:8000`.
`openapi-typescript` 7.13 declares a TypeScript 5 peer; `package.json`
`overrides` points it at our TS 6 (verified; `skipLibCheck` means the schema
is checked only through `client.ts`) — remove once upstream supports TS 6.
Dependencies for later phases are pre-installed (`three`, `d3-*`).

**Phase 1 — Contract.** `python -m stocktown openapi | openapi-typescript`
(`npm run gen:api`, no server needed); `schema.d.ts` committed and
Prettier-ignored. `createApi({ baseUrl, fetch })` → `Api`; errors throw
`ApiError { status, retryAfterSeconds }`; a dead network rejects with
`TypeError`. `parseLiveMessage` fails loud on unknown message types.

**Phase 2 — Stores and live feed.** `useUniverseStore.load(universeId)`
(universe + catalogue in parallel; a failed reload keeps the data).
`useFundamentalsStore` — command `load(ticker)` (once per ticker, in-flight
de-duplicated, failures retried) and query `entryFor(ticker)`, split so
nothing fetches inside a `computed`. `useLiveBar(ticker, openSocket?)` →
`{ bar, status }`: follows ticker changes, closes on unmount, `4404`/`4503`
reported without retry, other drops retried after 1s/2s/4s.

**Phase 3 — Routes and shell.** `createAppRouter(history)`; drawer as a
nested child route (`props: true`) so the view stays mounted underneath;
`UniverseLayout` loads the universe named in the URL and shows loading /
not-found / retry; List/City links carry the query. `format.ts`:
`formatPercent`, `formatRatio`, `formatMetricValue`.

**Phase 4 — List.** `filterPositions` / `sectorsIn` (`lib/positions.ts`);
`useQuerySort` / `useQueryFilters` keep state in the URL via
`router.replace` (two setters in the same tick would lose the first — batch
them if a "reset all" control is ever added); `PositionsTable` (props in,
events out; one column per catalogue metric; missing values sort last);
`FilterBar` (the input keeps its own text so keystrokes aren't lost while
the URL updates). Later: `ColumnPicker` + `useQueryColumns` (absent `cols`
= defaults; empty `cols=` = every metric hidden); hidden columns still sort;
long names truncated with the full name on hover.

**Backend follow-ups.** `last_close` on positions; `unit`/`scale`/`refresh`
as enums (fixed values in the generated TypeScript); `signed` on every
metric.

Tests so far: 114 frontend (Vitest) + 78 backend, all mutation-verified.
Shared helpers: `src/__tests__/fixtures.ts` (`TEST_PORTFOLIO`, `TEST_CATALOGUE`,
`TEST_INSTRUMENT`),
`src/__tests__/fakeApi.ts` (`fakeApi`, `piniaWith`),
`src/__tests__/renderApp.ts` (`renderAppAt`, `testPortfolioApi`; always
provides fake sockets), `src/__tests__/fakeSocket.ts` (`FakeSocket`,
`recordingSockets`); component
specs render with Testing Library and wait for navigation with `flushPromises`.

---

## Phase 5 — Popup (drawer)

Goal: clicking a row opens a working drawer with live price, city metrics
and fundamentals. The same drawer serves the city later.

**Prerequisites:** Phase 4 done. (Finnhub's dividend yield is a percent;
`services/instruments.py` already converts it to a fraction.)

**Progress:** shell done — non-modal Sheet open while its route is (a
modal one closed on the press, so the release opened a second drawer — a
visible flash when switching rows); closing
returns to the parent view (`route.matched`) with the query kept. Header
done — `DrawerHeader.vue` + pure `lib/quote.ts` (`headlineQuote`): live
price vs `last_close` once a bar's `session_date` is after the snapshot's,
otherwise last close + `day_change` ("Close, {date}"); `formatPrice`;
`OPEN_SOCKET_KEY` lets tests inject sockets. Metrics section done —
`CityMetricsSection.vue` lists every catalogue metric ("At the close,
{date}", since they're from the snapshot even while the header is live);
`formatMetricValue(value, metric)` puts "+" on signed metrics, in the table too.
Fundamentals done — `FundamentalsSection.vue` fetches once the drawer has
stayed on a ticker for 300 ms (non-modal switching makes flicking through
rows cheap; Finnhub is 60/min), nothing if closed sooner; placeholder / 404
"No fundamentals" / 503 "unavailable" + Retry; `formatCompactMoney`,
`formatOrDash`. Live status done — no separate live-bar section (one
minute's OHLC adds little; IEX volume is ~2–3% of true volume, so showing
it would mislead). Instead the header tag (`quoteTag`) shows the bar's
minute in market time (`minute_market` from the backend: "Live · 15:59 ET")
and connection problems ("reconnecting…", "live prices unavailable", "no
live prices for this ticker"); the normal first connect gets no note. Next:
the browser check.

**Deliverables:**

- `components/drawer/TickerDrawer.vue` — non-modal shadcn Sheet (`Esc`/X
  close; a press outside picks that row or building instead of closing),
  right side; closing returns to the parent view with the query kept. Calls
  `useLiveBar(ticker)` once and passes `bar`/`status` down as props.
- `DrawerHeader.vue` — ticker, name, sector, live price, day change against
  the position's `last_close` (`formatPercent(…, { showPlus: true })`).
  When the live bar is dated on or before `session_date` (market closed),
  show the `day_change` metric instead, or the live change would read ~0%.
- `CityMetricsSection.vue` — every catalogue metric with its formatted value.
- `FundamentalsSection.vue` — P/E, market cap (`formatCompactMoney`, added to
  `format.ts` here), dividend yield. `watch(ticker, load)` +
  `entryFor(ticker)`; skeleton while loading; 404 → "no fundamentals for this
  ticker"; 503 → "unavailable — retry".
- Live status in the header tag (`quoteTag`), replacing the planned
  `LiveBarSection.vue`: the bar's minute in ET, and 4404 / 4503 / retries
  exhausted / reconnecting as short notes.

**Tests:** `TickerDrawer.spec.ts` (opens for the route ticker, closes back
with the query), `quoteTag` in `quote.spec.ts` (each status),
`FundamentalsSection.spec.ts` (fake Api: loading → data → error);
`formatCompactMoney` in `format.spec.ts`.

**Done when:** in the browser, a row click shows the header immediately,
fundamentals within ~1–2s, "Live · HH:MM ET" during market hours (first
real check of the relative `/api/live` WebSocket URL); closing keeps sort
and filters.

**Checkpoints:** shell + open/close → each section → status handling →
browser check.

---

## Phase 6 — City view

Goal: the treemap city renders, responds to metric pickers, and a building
click opens the same drawer.

**Prerequisites:** Phase 5 done.

**Progress:** layout + scales done (`lib/cityLayout.ts`, `lib/cityScales.ts`).
Decisions (tune once seen in the browser):

- City 100 × 100 world units centred on the origin; heights 1–20 in the same
  units. Streets 1.5 between sectors, alleys 0.25 between neighbours.
- One d3 treemap call with padding per depth (street at the root, alley in
  a district) instead of two calls — same result, less code.
- Percentile metrics (6 of 7) use our own percentile rank: ties share the
  middle rank, a single or all-equal set sits at mid-height. d3's
  `scaleSequentialQuantile` maps between-values to the lower rank, all-equal
  to the top and a single value to `NaN`.
- Signed colours: RdBu inner 80%, white at 0, red losses, blue gains
  (colour-blind friendly); full strength at the 95th percentile of |moves|
  so one outlier doesn't wash the city out. Unsigned: plasma, following the
  metric's scale. Missing value: height 1, grey (zinc-400).
- Log metrics with zero or negative values fall back to linear; an
  all-equal set gets d3's midpoint (0.5).

Canvas skeleton done (`components/city/CityCanvas.vue`, `views/CityView.vue`):

- `CityView` is lazy-loaded; Three.js lives in its own chunk (~140 kB gzip,
  main bundle unchanged at ~110 kB). The build warns that this chunk
  (~560 kB minified, mostly Three.js) is over Vite's 500 kB default —
  expected, and deliberately not silenced: `chunkSizeWarningLimit` is global,
  so raising it would also stop guarding the main bundle. Investigate any
  *other* chunk over the limit.
- Without WebGL 2 (old browsers, and jsdom) the city shows a message linking
  to the list with the query kept — which is also what tests exercise.
  `CityCanvas` itself has no unit test (faked WebGL would only test the
  fake); the browser check covers it.
- One `InstancedMesh` of unit boxes (base on the ground, so `scale.y` is the
  height) draws every building; rendered on camera change and resize only,
  not every frame. Everything is disposed on unmount (GPU memory isn't
  garbage collected). Camera starts at (0, 90, 110); `MapControls` polar
  angle 15°–75° (never below ground), distance 15–300.
- Placeholder look until the pickers: every building 4 high, zinc-500.

**Deliverables:**

- Router: `CityView` loaded with `() => import(...)` so Three.js is only
  downloaded when the city is opened.
- `src/lib/cityLayout.ts` — pure: positions → buildings and districts
  (`{ x, z, width, depth }` + ticker/sector) via `d3.hierarchy` + one
  `d3.treemap` (street padding between districts, alley padding between
  buildings); `null` sector → Unclassified.
- `src/lib/cityScales.ts` — pure: height (`scaleLinear` / `scaleLog` /
  `scaleQuantile` → `[1, 20]`, log falls back to linear for non-positive
  values) and colour (plasma, or RdBu clipped and centred on 0 when
  `signed`; null → neutral grey).
- `useQueryMetrics` in `useQueryState.ts` — `?height=` / `?color=`.
- `components/city/MetricPickers.vue` (two shadcn Selects from the
  catalogue), `CityCanvas.vue` (one component owning the imperative Three.js
  scene: renderer, camera, `MapControls`, lights, ground, one
  `InstancedMesh`; `watch` rebuilds matrices/colours; render on change, not
  every frame; dispose everything on unmount), `SectorLabels.vue`
  (`CSS2DRenderer`), `BuildingTooltip.vue`, `Legend.vue`.
- Filters shared with the list: filtered-out buildings are dimmed.
- Hover: raycast on `pointermove` (per animation frame) → outline + 1.05×.
  Click → `city-ticker` route with the query kept; selected building gets a
  thicker outline.

**Tests:** `cityLayout.spec.ts` (area proportional to weight; one district
per sector containing its buildings; street/alley gaps between every pair),
`cityScales.spec.ts` (domain edges → `[1, 20]`; ranks and ties; log
fallback; 0 → white when signed; outlier saturation; null → grey). No component
test for `CityCanvas` (WebGL in jsdom isn't worth it) — browser check instead.

**Done when:** `/spy/city` renders the city with visible streets; pickers
update it and the URL; hover/click/drawer work; orbiting is smooth and the
camera can't go below ground; the legend follows the colour metric.

**Checkpoints:** pure layout + scales → canvas skeleton (fixed boxes) →
pickers → hover + tooltip → click → labels + legend → browser check.

---

## Phase 7 — Polish and accessibility

- Toasts (shadcn) for `Retry-After`-driven retries and one-off errors.
- Keyboard: the table becomes one tab stop with arrow-key row navigation
  (roving focus) instead of a tab stop per row; `Enter` opens the drawer;
  drawer `Esc` / focus returns to the row or building.
- Screen reader: drawer headings; `aria-live` on the live price.
- Empty states: no rows match the filters; direct link to a ticker that isn't
  in the universe.
- Remove any leftover scaffold.

**Done when:** keyboard-only use reaches every control in list + drawer;
toasts fire on 503s.

---

## Not in this plan

- **E2E tests (Playwright)** — until the list and drawer are stable
  (`npm init playwright` + one CI job).
- **CSV export** — roadmap.
- **Portfolio import** — roadmap; the UI is ready for it.
- **Persistence (SQLite)** — after the frontend. It enables
  stale-while-revalidate (serve the stored snapshot at once, rebuild in the
  background) and a daily pre-warm, so no visitor waits for the cold build
  (~10s today, varies with Alpaca).
- **Metric range filters, live city, building roofs/windows, city LOD,
  runtime WS validation (zod), locale detection** — not needed for the MVP.
- **Relationship "roads"** — corridors are reserved in the layout; nothing
  draws in them until the data exists.

## Sequencing rationale

- List (4) before drawer (5) before city (6): each verifies the data path
  more cheaply than the next, and the drawer is shared by both views, so it
  is built once against the simpler one.
- City last: Three.js is the biggest unknown, and with the other views green
  any problem is isolated to the canvas.
- Polish (7) last, so it isn't spent on code that gets rewritten.
