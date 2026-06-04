# Embpred Viability Predictor — demo

An embryo viability predictor for an IVF clinic. The product helps embryologists rank a patient's embryos by likelihood of producing a live birth, using a suite of computer-vision models that score morphology, morphokinetic stage, and chromosomal normality from timelapse imaging.

**Phase:** demo MVP. The prediction pipeline is out of scope here — the goal is to showcase how prepopulated predictions feed clinical UX workflows on a single fabricated patient. See `CLAUDE.md` for the domain glossary and data hierarchy.

## Implemented

- **Postgres schema** (`backend/db/`): composite natural keys, custom `box` type for bounding boxes, `morphokinetic_stage` / `ploidy_class` enums, full Alembic migration.
- **Ingest pipeline** (`scripts/ingest.py`): seeds 1 patient + 10 embryos + ~25k images + ~16k real predictions (bbox + stage) from disk, plus 20 deterministic fabricated predictions (ploidy + live-birth).
- **FastAPI app** (`backend/api/`): 4 endpoints serving the 3 demo workflows (patient overview, focal scroll, morphokinetic timeline) + a sandboxed image proxy.
- **Workflow SQL** (`backend/db/queries/`): per-workflow `.sql` files as living spec, runnable via `psql -f`.
- **Frontend** (`frontend/`): Vite + React 19 + TypeScript, Tailwind v4, React Router v7, TanStack Query v5. Three workflows wired end-to-end — ranked patient overview, keyboard-driven focal scroll with bbox overlay, and the morphokinetic timeline.
- **Docs** (`docs/`): brief api + database references, plus pedantic PostgreSQL notes drawn from this codebase.

## Not yet

- **Live-birth real predictions** — currently `fabricated-v0`; production model not yet wired.
- **Multiple patients** — one fabricated patient (`patient1`) for the demo.

## Quickstart

Requires Postgres 15 running locally and `data/patient1/` populated.

```bash
make install      # create .venv, install Python deps
make db.reset     # drop, recreate, migrate the embpred database
make db.ingest    # populate from data/patient1
make api          # uvicorn on :8000

# frontend (separate terminal; needs Node 20+)
cd frontend && npm install
make front        # Vite dev server on :5173 → proxies API at :8000
```

The UI defaults to `http://localhost:8000` for the API; override with `VITE_API_BASE`.

## Where to look

| Path | What |
|---|---|
| `CLAUDE.md` | Domain glossary, data hierarchy, conventions |
| `docs/api.md` | Endpoint reference |
| `docs/database.md` | Schema + custom types |
| `docs/postgres.md` | Pedantic Postgres notes |
| `plans/` | Frontend workflow envisioning + database design notes |
