# Embpred demo frontend

Demo UI for the embryo viability predictor. Showcases three embryologist
workflows over seeded/fabricated single-patient data. Optimized for demo
legibility and fast local iteration, not production hardening.

## Stack

- **Vite + React 19 + TypeScript** — SPA, no SSR.
- **Tailwind v4** via `@tailwindcss/vite` (no config file; `@import "tailwindcss"` in `src/index.css`).
- **React Router v7** (unified `react-router` package).
- **TanStack Query v5** — all server state. No Redux/Context store; the query cache *is* the store.

## Run

```bash
npm install
npm run dev        # Vite on :5173  (or `make front` from repo root)
npm run build      # tsc -b && vite build
npx tsc --noEmit   # typecheck only
```

Expects the FastAPI backend on `http://localhost:8000`. Override with
`VITE_API_BASE` (e.g. in `.env.local`).

## Layout

```
src/
├── main.tsx            # entry: QueryClientProvider (staleTime 60s, no refetch-on-focus)
├── App.tsx             # BrowserRouter + routes, all wrapped in <AppShell>
├── lib/api.ts          # API base, fetch helper, TS types mirroring backend schemas, `api.*` methods
├── components/
│   ├── AppShell.tsx        # sidebar patient selector (GET /patients) + main content slot
│   ├── MorphokineticBar.tsx# reusable stage bar: segments + collision-aware milestone labels
│   └── FrameGrid.tsx       # synchronized multi-embryo focal scroll (comparison "grid" tab)
└── pages/
    ├── PatientOverview.tsx # ranked embryos: top-3 cards + dense list, two-state ploidy dot
    ├── FocalScroll.tsx     # single embryo: focal-stack viewer, bbox overlay, keyboard nav
    ├── Timeline.tsx        # single embryo: morphokinetic bar + milestone table
    └── Comparison.tsx      # all embryos: tabs → stacked timelines | frame grid
```

## Routes

| Path | Page |
|---|---|
| `/` | redirect → `/patients/patient1` |
| `/patients/:patientId` | PatientOverview |
| `/patients/:patientId/compare` | Comparison (Timelines / Frame grid tabs) |
| `/patients/:patientId/embryos/:embryoLabel/timepoints/:timepoint` | FocalScroll |
| `/patients/:patientId/embryos/:embryoLabel/timeline` | Timeline |

## Architecture & conventions

- **All server access goes through `lib/api.ts`.** Types there mirror
  `backend/api/schemas.py` by hand — when you add/change an endpoint, update
  both the type and the `api.*` method here. Components never call `fetch`
  directly.
- **Image URLs are server-relative** (`/images/...`); wrap with `apiUrl()`
  before putting them in `src`. The backend translates these to disk paths.
- **Query keys are positional tuples**, e.g. `['focal', patientId, label, tp]`,
  `['patient', id]`, `['comparison', id]`. Reuse the exact same key shape when
  prefetching so cache hits line up (see neighbor prefetch in FocalScroll /
  FrameGrid).
- **Navigation entering an embryo lands on `timepoints/0`** (start of timelapse)
  by convention — see `embryoHref` in PatientOverview and the embryo-switch in
  FocalScroll.
- **Ploidy is folded to two states for display.** Backend reports
  euploid/aneuploid/mosaic; the UI calls `foldPloidy()` (mosaic → aneuploid)
  and shows a colored dot with no numeric score. Keep this fold in the frontend;
  the API stays faithful.
- **`MorphokineticBar` is the shared timeline primitive.** It takes a
  `Timeline`-shaped object (`{num_timepoints, stream, milestones}`); pass
  `showLabels={false}` for compact/stacked use and `onJump` to make segments
  clickable. Stage colors are exported as `STAGE_COLORS`.
- **Keyboard nav** (`FocalScroll`, `FrameGrid`) uses a `window` keydown listener
  in `useEffect`; arrows = time, up/down = focal depth, `⌘/ctrl`+arrows or grid
  conventions documented in-component. Always `preventDefault` to stop scroll.
- **Snappiness pattern**: `placeholderData: keepPreviousData` on the active
  query + `queryClient.prefetchQuery` for neighbor frames. Note: this warms the
  *JSON*, not image bytes — see the perf notes below.

## Extending

- **New workflow/page**: add the `api.*` method + types in `lib/api.ts`, create
  the page in `pages/`, register the route in `App.tsx`. It renders inside
  `AppShell` automatically (sidebar + main).
- **Multiple patients**: already wired — the sidebar reads `GET /patients` and
  the active id comes from the URL. Seed more patients in the DB and they show up.
- **New per-stage color / stage**: extend `STAGE_COLORS` in `MorphokineticBar`.

## Known perf caveats (focal/grid scroll)

The synchronized grid scroll flickers and is heavier than ideal. Root causes:
per-frame JSON round-trips, full-res 800×800 JPEGs downscaled in-browser, and
`<img key={url}>` remounting on each step. Durable fixes (not yet done):
per-embryo manifest endpoint, thumbnail derivatives + cache headers, and
double-buffering with `img.decode()` neighbor preloading instead of remounting.
