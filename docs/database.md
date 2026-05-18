# Database layer

Postgres 15 + SQLAlchemy 2 + Alembic. Code under `backend/db/`.

## Tables

```
patients          (external_id PK, name, date_of_birth, office, created_at)
   │ 1:N
embryos           (patient_external_id PK/FK, label PK, num_timepoints,
   │ 1:N            date_seeded, well, thumbnail_timepoint)
   ├── images                  (..., timepoint PK, focal_depth PK, path)
   ├── bbox_predictions        (..., timepoint PK, model_version PK, bbox: box)
   ├── timepoint_predictions   (..., timepoint PK, model_version PK, stage: enum)
   ├── ploidy_predictions      (..., model_version PK, predicted_at, ploidy: enum, score: real)
   └── live_birth_predictions  (..., model_version PK, predicted_at, score: real)
```

All children carry `(patient_external_id, embryo_label)` as the leading PK columns and cascade-delete from `embryos`.

## Conventions

- **Composite natural keys.** No surrogate ids. `(patient_external_id, embryo_label, ...)` is the lookup pattern everywhere, including in API URLs.
- **`model_version` is part of the PK** for prediction tables — multiple model versions of the same prediction coexist without conflict.
- **Fabricated rows are marked by their `model_version`** — `fabricated-v0` for synthetic ploidy + live_birth. Real predictions use `frcnn-v1` (bbox) and `timelapse-v1` (stage).
- **Images on disk, paths in DB.** `images.path` is an S3-style logical key (`patients/<id>/embryos/<label>/F<depth>/<file>`); the API resolves it to either disk or S3 at request time.

## Custom types

- **`BBox`** dataclass + `Box` SQLAlchemy `UserDefinedType` in `backend/db/types.py` adapt the native Postgres `box`. Bound via `CAST(:value AS box)`; read back as `BBox(ul_x, ul_y, lr_x, lr_y)` (normalized regardless of Postgres' internal point ordering).
- **Postgres ENUMs** `morphokinetic_stage` and `ploidy_class` are defined in the migration; Python `Enum` mirrors live in `backend/db/enums.py`. Order in the enum definition is the canonical biological order (`t1, tPN, tPNf, t2, ..., tEB, tEmpty`).

## ORM relationships

Every prediction/image table has `embryo: relationship(back_populates="...")` on the child and a matching collection on `Embryo`, with `cascade="all"` + `passive_deletes=True`. The ORM defers parent-delete cleanup to the DB's `ON DELETE CASCADE`.

## Commands

```bash
make db.reset      # drop, recreate, migrate
make db.migrate    # alembic upgrade head
make db.ingest     # scripts/ingest.py: patient + embryos + images + real + fabricated preds
make db.psql       # psql shell
```

## Workflow queries

`backend/db/queries/workflow_*.sql` — one per UX workflow, runnable with `psql -f`. These mirror what the API returns and serve as living spec for new endpoints.

## Migrations

Hand-write Alembic revisions for changes that involve enums or the `box` type — autogenerate doesn't know about custom `UserDefinedType` or `postgresql.ENUM` cleanly. See `backend/alembic/versions/0001_init.py` for the pattern (declare a local `_Box(UserDefinedType)`, `enum.create(bind)` then reference by name in subsequent columns).
