You are an expert in database schema design. Your job to (a) design the database informed by the use cases and then (b) populate them with data via datapipelinig.

Suggested tables (open to push back or redesign):

Raw tables:
- patient record: patient id, embryo id, age, name, office
- embryo record: patient id, embryo id, number of frames, date seeded

Prediction tables
- RCNN prediction: embryo id, focal depth, timpepoint index, bbox1,bbox2,bbox3,bbox4, model faster
- Timepoint predicitons: embryo id, focal depth, timepoint index, stage prediction, model version, 
- ploidy prediction: embryo id, date predicted, score, model version
- live birth prediction: embryo id, date predicted, score, model version


Scan for any missing column or information that should be included in the information. Inform our schema design using doc plans/frontend_workflows.md

---

## Data pipelining

See `CLAUDE.md` for the on-disk tree. Headline rules:

1. **Join `timepoint` ↔ filepath by sorting on `RUN<int>`.** CSVs have no
   filenames; the only link is positional. For each focal-depth folder,
   sort files by the integer in `..._RUN<int>.jpeg` (not lex — `RUN1,
   RUN10, RUN11` lex-sorts wrong). The i-th sorted file is `timepoint =
   i` in both `Emb{N}_bboxes.csv` and
   `Emb{N}_postprocessed_timelapse_outputs.csv`.

2. **Assert per embryo:** `F-15`, `F0`, `F15` have equal frame counts
   `K`; both CSVs have `K` rows with contiguous `timepoint = 0..K-1`.
   Fail loudly on mismatch.

3. **Bbox CSV cells are Python-tuple strings** (`"(360, 221)"`). Parse
   with `ast.literal_eval`. Blank cells + `class_name = "tEmpty"` mean
   the embryo was removed — keep the row, store `NULL` corners and
   `tEmpty` stage. Don't drop or sentinel-fill.

4. **Embryo id = folder name** (`Emb1..Emb10`). The `WELL<w>` token in
   filenames is **not** the same integer (e.g. `Emb1` → `WELL2`).

5. **Bbox is per-(embryo, timepoint)**, not per focal depth — one row
   shared across all 3 depths. Drop `focal_depth` from the rcnn table.

6. **Fabricate** `ploidy_prediction` and `live_birth_prediction` (not on
   disk). Use `model_version = "fabricated-v0"`, seeded by
   `(patient_id, embryo_id)`. Real bbox/timepoint rows must use a
   non-fabricated `model_version` so the UI can distinguish them.

