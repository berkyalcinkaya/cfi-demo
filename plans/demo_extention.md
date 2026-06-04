# Demo extension — multi-patient roster, admin panel, mock auth

## Goal

Make the demo more compelling to a **private-practice fertility clinic
administrator**: more embryo data (a **roster of 6 patients**), a simulated
**admin panel** (ingest log + recently-evicted embryos + "coming soon"
affordances), and a **mock authentication** gate on startup.

The admin panel is *simulated* but should be backed by **real (fabricated)
tables**, not hardcoded JSON. This doubles as groundwork for `infra_plan.md`
(the `inference_runs` ledger and `images.evicted_at` come straight from it),
which reads better to an administrator than a static mock.

## Read first

- `plans/infra_plan.md` — source of the `inference_runs` ledger (§Schema
  deltas) and `images.evicted_at` eviction model (§Disk pressure). This PR
  builds the demo-facing slice of both.
- `plans/database_seed.md`, `docs/database.md`, `docs/postgres.md` — schema +
  data-pipeline rules.
- `scripts/ingest.py`, `backend/db/models.py`, `backend/api/main.py` — the code
  you will modify.

## Invariants (do not break)

- **The API is a read-only seam.** Admin endpoints `SELECT` from tables; they do
  not special-case where data came from (`infra_plan.md` opening invariant).
- **Determinism.** `make db.reset && make db.ingest` must be fully reproducible
  and re-runnable. No runtime randomness without a fixed seed. Fabrication is
  already seeded by `sha256(patient:embryo)` in `seed_fabricated_predictions` —
  reuse that pattern.
- **Fabricated rows are marked by `model_version`** (`fabricated-v0`). Keep this
  convention for any new fabricated predictions (`docs/database.md`).
- **Images on disk, paths in DB.** `get_image` resolves
  `DATA_DIR/{patient_id}/images/{embryo}/{focal_dir}/{file}` (main.py). Any new
  patient needs real files on disk at that path and matching `images.path` rows.

---

## Deliverable 1 — Six-patient roster from recycled embryos

**End state: 6 patient records, each with 4–7 embryos.** Every embryo is a
*duplicate* of one of the existing 10 source embryos, seed-randomly selected per
patient. Embryos intentionally will be **duplicated across patients** (the same
source embryo may back embryos for several patients). Keep Jane Cooper
(`patient1`) as one of the six for continuity; fabricate identities for the
other five.

### The 10 embryos become a read-only source library

The existing `data/patient1/` tree (10 embryos `Emb1`–`Emb10` + their `bbox` and
`timepoints` CSVs) is the **canonical source library**. Treat it as read-only —
do **not** seed any patient in place from it, or generation would clobber the
only copy of the source images.

1. **Snapshot the library (idempotent).** Ensure a read-only source copy exists,
   e.g. `data/source_embryos/{images,predictions}`. If absent, copy it from the
   current `data/patient1/`. All patient generation reads from here. Do **not**
   commit copied/generated images.

### Strategy (seeded-random — random-looking but fully reproducible)

The requirement is "randomly selected," but `CLAUDE.md` demands re-runnable
seeds. Reconcile with a **single fixed global seed** (e.g. `DEMO_SEED = 1337`)
so selection is varied yet identical on every `make db.ingest`.

1. **Define the roster.** A `PATIENTS` config of 6 entries — each with
   `external_id` (`patient1`..`patient6`), fabricated `name`, `date_of_birth`,
   `office` (`patient1` = Jane Cooper, unchanged identity).

2. **Per patient, pick embryos deterministically.** Seed a `random.Random` from
   `(DEMO_SEED, external_id)`. Draw `n ∈ [4, 7]`, then sample `n` **distinct**
   source embryos from the 10. Relabel the chosen sources to clean contiguous
   labels `Emb1..Embn` (per-patient mapping); collisions across patients are
   fine — PKs include `patient_external_id`.

3. **Generate each patient's data tree (rename-on-copy).** CSV *contents* are
   label-agnostic (columns `timepoint`, `bbox_*`, `class_name`), so relabeling
   is filename-only:
   - `data/source_embryos/images/<src>/F*/*` → `data/<patient>/images/<dest>/F*/*`
   - `data/source_embryos/predictions/bbox/<src>_bboxes.csv` →
     `data/<patient>/predictions/bbox/<dest>_bboxes.csv` (same for the
     `_postprocessed_timelapse_outputs.csv` files)
   - Put this in a new idempotent `scripts/generate_patients.py` (clears each
     `data/<patient>/` first; emits the chosen mappings for the log).

4. **Predictions.** Timepoint + bbox rows come from the copied CSVs verbatim
   (real `frcnn-v1` / `timelapse-v1`). Fabricated ploidy + live-birth are
   produced by the **existing** `seed_fabricated_predictions`, keyed on
   `(patient, label)` — deterministic and distinct per patient for free. Do
   **not** permute values by hand.

5. **Refactor `scripts/ingest.py` for the roster.** Today `main()` hardcodes
   `PATIENT_SEED` and does delete-then-insert on `patient1` only
   (ingest.py:309-311). Change to iterate the `PATIENTS` config, **delete all
   roster patients** before insert, and seed each from its own
   `data/<patient>/` tree.

**Verify:** every patient has 4–7 embryos; across the roster each patient has
≥1 embryo reaching a blastocyst stage (`tB`/`tEB`) so `thumbnail_timepoint` is
non-null and cards render thumbnails. 

---

## Deliverable 2 — `inference_runs` ledger (the "ingest table")

Realize the ledger from `infra_plan.md` §Schema deltas as a real table, seeded
with **fabricated** rows for every embryo across all six patients.

**New table `inference_runs`** (hand-write the Alembic migration per
`docs/database.md` — autogenerate mishandles enums/custom types):

| column                                  | notes |
| --------------------------------------- | ----- |
| `run_id` (PK, text)                     | e.g. `run-{uuid4}` or `{model}-{patient}-{embryo}` |
| `patient_external_id`, `embryo_label`   | composite FK → `embryos`, `ON DELETE CASCADE` |
| `model_version`                         | one run per real model per embryo: `frcnn-v1`, `timelapse-v1`, `fabricated-v0` |
| `tp_start`, `tp_end` (int, nullable)    | timepoint range processed |
| `status` (enum `run_status`)            | `succeeded` / `failed` / `running`; all should be `succeeded` |
| `rows_written` (int)                    | fabricated count |
| `started_at`, `finished_at` (timestamptz) | deterministic recent "nightly" timestamps |

Seeding (in `ingest.py`, fabricated + deterministic): emit one run per
`(embryo, model_version)`. Make timestamps look like recent nightly batches.
Include **one** `failed` run so the panel looks real (mirrors `infra_plan.md`
"nightly failure → resumable").

**Endpoint** `GET /admin/ingest-runs` → newest-first list. Add `IngestRunOut` to
`backend/api/schemas.py`.

---

## Deliverable 3 — Admin view

A new gated `/admin` page (React Router) with three sections:

1. **Ingest log** — table from `GET /admin/ingest-runs`: embryo, model_version,
   tp-range, status (color-coded), rows_written, finished_at.

2. **Recently evicted embryos** — backed by `images.evicted_at`
   (`infra_plan.md` §Disk pressure). Add a **nullable `evicted_at timestamptz`**
   column to `images`. In `ingest.py`, fabricate eviction on the **2 oldest
   embryos across the roster** (by `date_seeded`) by stamping `evicted_at` on
   all their image rows, so the panel spans multiple patients. Endpoint
   `GET /admin/evicted` returns embryos that have any evicted
   image: `{patient, label, evicted_at (max), num_images}` + a "served from cold
   storage" hint. Add `EvictedEmbryoOut` schema.
   *Out of scope:* `embryos.culture_ended_at` / `disposition` / the evictor
   daemon itself (separate infra deliverable).

3. **Coming-soon affordances** — non-functional, visibly-disabled cards for
   **Audit Log**, **User Management**, **Model Registry**. Pure UI placeholders
   ("Coming soon"); no endpoints.

---

## Deliverable 4 — Mock authentication (client-only)

A login screen shown on startup before the app is usable.

- **New `frontend/src/pages/Login.tsx`** + a route guard. Unauthenticated users
  are redirected to `/login`.
- Accept any non-empty email + password (or hardcode one demo credential, e.g.
  `admin@carolinafertility.com`). On submit, set `localStorage.embpred_auth`
  and a display name.
- "Sign out" in `AppShell` clears the flag → back to `/login`.
- Frame it as the realistic counterpart to `infra_plan.md`'s "registered
  devices only", but **mock only**.

**Non-goals (do not build):** no backend auth, no JWT/refresh tokens, no users
table, no password hashing, no real sessions/cookies. It is a client-side gate.

---

## File-level change map

**Backend**
- `backend/db/models.py` — add `InferenceRun`; add `Image.evicted_at`.
- `backend/db/enums.py` — add `RunStatus` enum.
- `backend/alembic/versions/000X_*.py` — hand-written: `run_status` enum +
  `inference_runs` table + `images.evicted_at`.
- `scripts/generate_patients.py` — new; snapshot source library + seed-randomly
  select 4–7 embryos per patient and copy+relabel images & CSVs into each
  `data/<patient>/` (idempotent; fixed `DEMO_SEED`).
- `scripts/ingest.py` — roster refactor; delete all roster patients; seed all 6
  from their generated trees; seed `inference_runs`; stamp `evicted_at`.
- `backend/api/main.py` — `GET /admin/ingest-runs`, `GET /admin/evicted`.
- `backend/api/schemas.py` — `IngestRunOut`, `EvictedEmbryoOut`.

**Frontend**
- `frontend/src/lib/api.ts` — new types + `getIngestRuns`/`getEvicted`; auth
  helpers (mirror schemas, per existing comment convention).
- `frontend/src/pages/Login.tsx`, `frontend/src/pages/Admin.tsx` — new.
- `frontend/src/components/AppShell.tsx` — Admin link + Sign out.
- `frontend/src/App.tsx` — `/login`, `/admin` routes + auth guard.

---

## Acceptance criteria

- `make db.reset && make db.ingest` runs clean and **idempotently** (re-runnable;
  identical output every run for a fixed `DEMO_SEED`).
- `GET /patients` returns **6** patients; each has **4–7** embryos; `patient1` is
  Jane Cooper.
- Image URLs resolve for **all** patients (cards show thumbnails; focal stacks
  load).
- `GET /admin/ingest-runs` returns fabricated runs for every embryo incl. one
  `failed`; `GET /admin/evicted` returns ≥1 embryo.
- The app redirects to `/login` when unauthenticated; signing in reveals the
  patient UI and the Admin page; Sign out returns to `/login`.
- No new linter/type errors; API seam unchanged for existing endpoints.

## Out of scope

Real auth/users/sessions; the evictor daemon, `culture_ended_at`, `disposition`;
S3/RDS migration; any change to existing prediction semantics or workflow
endpoints.
