# API layer

FastAPI app at `backend/api/`. One file per concern:

- `main.py` — routes, CORS, image-serving sandbox
- `schemas.py` — Pydantic response models

## Running

```bash
make api                       # uvicorn --reload on :8000
```

Override via `DATABASE_URL` env var (defaults to `postgresql+psycopg://localhost/embpred`).

## Endpoints

Each maps 1:1 to a workflow query under `backend/db/queries/`.

| Verb | Path | Workflow | Returns |
|---|---|---|---|
| `GET` | `/health` | — | `{"status":"ok"}` |
| `GET` | `/patients/{patient_id}` | 1: overview | Patient + embryo cards (ranked by `live_birth` desc, NULLS last) |
| `GET` | `/patients/{patient_id}/embryos/{label}/timepoints/{tp}` | 2: focal scroll | 3 focal-image URLs + shared `bbox` + `stage` |
| `GET` | `/patients/{patient_id}/embryos/{label}/timeline` | 3: timeline | Full `stream` (every tp+stage) + `milestones` (first-seen per stage) |
| `GET` | `/images/{patient_id}/{label}/{focal_dir}/{filename}` | — | Raw JPEG bytes |

All non-image responses are JSON. Predictions include `is_fabricated` (true when `model_version` starts with `fabricated-`) so the UI can badge synthetic data.

## Image serving

The DB stores **S3-style logical keys** like `patients/patient1/embryos/Emb1/F0/RUN522.jpeg`. The API exposes them at a flatter URL:

```
DB key:  patients/patient1/embryos/Emb1/F0/<file>
URL:     /images/patient1/Emb1/F0/<file>
Disk:    data/patient1/images/Emb1/F0/<file>
```

`_image_url()` in `main.py` rewrites DB → URL. `get_image()` resolves URL → disk under `DATA_DIR`, then guards with:

1. Extension whitelist (`.jpeg`, `.jpg`, `.png`)
2. `candidate.resolve().relative_to(DATA_DIR.resolve())` — blocks traversal even if a `..` slips through path parsing

## Errors

- `404` — patient/embryo/timepoint not found; out-of-range `tp` (validated against `embryos.num_timepoints`)
- `400` — disallowed image extension; resolved path escapes `DATA_DIR`

## Adding an endpoint

1. Add a Pydantic response model in `schemas.py`
2. Add the route in `main.py` (use `Depends(get_session)` for DB access)
3. Mirror the SQL in `backend/db/queries/` so the query is documented and runnable via `psql -f`
