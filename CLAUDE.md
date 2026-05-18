# Embpred Viability Predictor 
Embryo viability predictor for an IVF clinic. A suite of computer vision
models that helps embryologists rank a patient's embryos by likelihood of
producing a live birth. **Current phase: demo MVP** — the goal is to showcase
frontend workflows end-to-end on fabricated/seed data while also laying the groundwork for shipping a production workflow.

While thinking ahead is an important, when in doubt, optimize for *demo legibility*: clear data shapes, deterministic seeded predictions, fast local iteration.

The application: showcase a few high impact frontend workflows (TBD) with a database that contains tables with patient data, embryo and timepoint predictions, 

Technology:
Backend: Python FastAPI
Database: PostegreSQL 15 running locally 
Frontend: in progress. goal: optimize for demo speed

---

## Domain glossary

These are non-obvious terms the codebase will use freely. If a name appears
in code or docs without explanation, it's defined here.

- **Patient** — the top-level entity. A patient has many embryos; the
  clinical question is which embryo to implant.
- **Embryo** — one fertilized egg from a given patient, imaged over time as
  it develops in a petri dish.
- **Timepoint** — a single moment in an embryo's timelapse. Each timepoint
  contains **7 images at different focal depths** (a focal stack).
- **Focal depth** — vertical slice through the embryo. Folder names use the
  convention `F-15`, `F0`, `F+15` etc., where the number is the offset in
  micrometers from the center focal plane (`F0`). 
- **Image**: Focal depth folders contain the raw images (see data hierarchy below). Thus if an embryo has f focal depths and n timepoints, then there are n*f images per embryo.
- **Bbox Prediction**: A Faster-RCNN generated 4-tuple that crops the wider focal depth image to focused image on the embryo itself. 
- **Morphokinetic stage** — labeled developmental milestones along the
  timelapse. Canonical stages used by this project, in order:
  `t1, tPN, tPNf, t2, t3, t4, t5, t6, t7, t8, tM, tB, tEB`.
  (tPN/tPNf = pronuclei appearance/fade; t2–t8 = cell-count divisions;
  tM = morula; tB = blastocyst; tEB = expanded blastocyst.)
- **Ploidy** — chromosomal normality. Predicted as euploid or aneuploid.
  mosaic. Per-embryo, not per-timepoint. 
- **Live birth prediction** — per-embryo probability of resulting in a
  live birth if implanted. The headline product output. *Coming soon* —
  for the MVP this is fabricated and should be indicated as such.

---

## Predictions
Predictions will be computed using batch computation that runs in the background on cloud. Thus, the prediction pipeline is out of the scope of this project. Assumption: database is prepopulated with predictions and the demo should show how this data can be leveraged within the UI. 

Predictions we will utilize:
1. Bounding box predictions (per image)
2. Timepoint predictions (per timepoint)
3. Ploidy prediciton (per embryo)
4. Live birth prediction (per embryo) - coming soon

**Note**: we will be seeding the database with semi-fabricated single patient for this demo. 

## Data hierarchy

Raw images live under `data/patient1/images/`; seeded model outputs live
under `data/patient1/predictions/`. Conceptually:

```
Patient
└── Embryo (many per patient, e.g. Emb1..Emb10)
    └── Timepoint (many per embryo but differ across embryos, ordered in time)
        └── FocalImage (exactly 7 per timepoint, one per focal depth)
```

For a single patient, observe the following structure:

```
patient1/
├── images/
│   ├── Emb1/
│   │   ├── F-15/           # focal-depth images for this depth across all timepoints
│   │   ├── F0/
│   │   │   ├── D2024.05.18_S00087_I5054_P_WELL2_RUN1.jpeg
│   │   │   ├── D2024.05.18_S00087_I5054_P_WELL2_RUN2.jpeg
│   │   │   ├── ...
│   │   │   └── D2024.05.18_S00087_I5054_P_WELL2_RUNK.jpeg  # K timepoints, consistent across focal depths
│   │   └── F15/
│   ├── Emb2/
│   │   └── ...
│   └── EmbN/
└── predictions/
    ├── bbox/                                       # Faster-RCNN crops, one CSV per embryo
    │   ├── Emb1_bboxes.csv                         # cols: timepoint, bbox_ul, bbox_ur, bbox_lr, bbox_ll
    │   └── ...                                     # Emb2..Emb10
    └── timepoints/                                 # morphokinetic stage per timepoint, one CSV per embryo
        ├── Emb1_postprocessed_timelapse_outputs.csv  # cols: timepoint, class_index, class_name
        └── ...                                     # Emb2..Emb10
```

Notes:
- Folder names for focal depth use `F-15`, `F0`, `F15` (no `+` sign on
  disk); treat the integer as the source of truth, not the string.
- The MVP assumes 3 focal depths in the demo dataset even though clinical
  data has 7 — confirm with a fresh `ls` before writing parsing code.
- Predictions on disk currently cover only **bbox** (per image/timepoint)
  and **timepoint stage** (per timepoint). Ploidy and live-birth
  predictions are not yet seeded — fabricate them at DB-load time.
- Bbox and timepoint CSVs are keyed by integer `timepoint` index, which
  joins back to the K-th image in each focal-depth folder.

---

## Repository layout

```
embpred/
├── CLAUDE.md              # this file
├── docs/                  # stable reference documentation
├── plans/                 # one-shot task specs (read with @plans/...)
├── .claude/
│   ├── agents/            # subagents (added reactively, not upfront)
│   └── commands/          # slash commands for repeated workflows
├── backend/               # API + DB (TBD framework)
├── frontend/              # demo UI (TBD framework)
├── data/
│   └── patient1/             # deterministic demo patient data
│       ├── images/           # source timelapse trees by embryo/focal depth
│       └── predictions/      # seeded model outputs
│           ├── bbox/         # Faster-RCNN crops, per-embryo CSV
│           └── timepoints/   # morphokinetic stage per timepoint, per-embryo CSV
└── scripts/               # migration, fabrication, one-off tools
```

## Conventions

- **Predictions are versioned.** Every prediction row carries a
  `model_version` string. Fabricated predictions use `model_version =
  "fabricated-v0"` so they're trivially distinguishable from real ones.
- **Images on disk, paths in DB.** All imageds will eventually live in s3 but exist on disk for the purpose of the demo. No images will live in the database, so rows reference paths on disk (but should mimic object storage paths for future portability).
---

## Commands
To be filled in once the stack is chosen. Placeholders:
```bash
# install
# (tbd)

# run dev backend
# (tbd)

# run dev frontend
# (tbd)

# migrate raw data → DB
# python scripts/ingest.py --src data/raw --db ...

# fabricate predictions
# python scripts/fabricate.py --seed 42

# tests
# (tbd)
``
