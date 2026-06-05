# Embpred Viability Predictor — demo

An embryo viability predictor for an IVF clinic. The product helps embryologists rank a patient's embryos by likelihood of producing a live birth, using a suite of computer-vision models that score morphology, morphokinetic stage, and chromosomal normality from timelapse imaging.

**Phase:** demo MVP. The prediction pipeline is out of scope here — the goal is to showcase how prepopulated predictions feed clinical UX workflows on a single fabricated patient. See `CLAUDE.md` for the domain glossary and data hierarchy.

## AI models

Four computer-vision models feed the workflow, chained from raw timelapse frames to a ranked list of embryos. Each writes its own versioned prediction table. The two upstream models (`frcnn-v1`, `timelapse-v1`) have real predictions seeded from disk; the two per-embryo models (ploidy, live-birth) are fabricated for the demo (`fabricated-v0`).




| #   | Model                                | Version         | Granularity   | Output                               |
| --- | ------------------------------------ | --------------- | ------------- | ------------------------------------ |
| 1   | Embryo localizer (Faster R-CNN)      | `frcnn-v1`      | per image     | bounding-box crop                    |
| 2   | Morphokinetic stage classifier       | `timelapse-v1`  | per timepoint | stage `t1…tEB`                       |
| 3   | Ploidy classifier                    | `fabricated-v0` | per embryo    | euploid / aneuploid / mosaic + score |
| 4   | Live-birth predictor *(coming soon)* | `fabricated-v0` | per embryo    | live-birth probability               |


Between the stage classifier and the embryo-level models, the raw per-frame stage predictions are **smoothed and monotonically decoded** (stages only advance: `t1 ≤ … ≤ tEB`) — this deterministic post-processing is what lands on disk as `*_postprocessed_timelapse_outputs.csv`. The two embryo-level models then run only once the decoded stage reaches a blastocyst (`tB`/`tEB`). See `plans/infra_plan.md` for the batch scheduling and `model_version` rollout strategy.

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


| Path               | What                                                  |
| ------------------ | ----------------------------------------------------- |
| `CLAUDE.md`        | Domain glossary, data hierarchy, conventions          |
| `docs/api.md`      | Endpoint reference                                    |
| `docs/database.md` | Schema + custom types                                 |
| `docs/postgres.md` | Pedantic Postgres notes                               |
| `plans/`           | Frontend workflow envisioning + database design notes |


