"""Step 2: seed the 6-patient roster + their embryos from the generated trees.

Re-runnable: regenerates the patient trees (scripts/generate_patients.py), then
deletes every roster patient row (cascading children) before re-inserting. Also
seeds the fabricated `inference_runs` ledger and stamps `images.evicted_at` on
the oldest embryos — the demo-facing slice of infra_plan.md.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import random
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, insert, update
from sqlalchemy.orm import Session

from backend.db.enums import MorphokineticStage, PloidyClass, RunStatus
from backend.db.models import (
    BboxPrediction,
    Embryo,
    Image,
    InferenceRun,
    LiveBirthPrediction,
    Patient,
    PloidyPrediction,
    TimepointPrediction,
)
from backend.db.session import engine
from backend.db.types import BBox

# Sibling import — `make db.ingest` runs `python scripts/ingest.py`, so the
# scripts dir is on sys.path[0]. generate_patients owns the roster + data trees.
from generate_patients import DATA_DIR, OFFICE, PATIENTS, generate

BLASTOCYST_STAGES = {"tB", "tEB"}

# Deterministic "nightly batch" timing for the fabricated inference_runs ledger.
# Anchored to a fixed constant (NOT now()) so output is byte-identical per run.
NIGHTLY_ANCHOR = datetime(2026, 6, 4, 2, 0, tzinfo=timezone.utc)
NIGHTS = 4  # spread embryo batches across the last 4 nights
EVICTION_ANCHOR = datetime(2026, 6, 2, 4, 30, tzinfo=timezone.utc)
NUM_EVICTED = 2  # oldest-by-date_seeded embryos to mark evicted, across the roster
# The one run we flag as failed so the admin panel looks real (infra_plan.md
# "nightly failure → resumable"). Emb3 always exists (every patient has ≥4).
FAILED_RUN = ("patient2", "Emb3", "frcnn-v1")

FOCAL_DEPTHS: tuple[tuple[int, str], ...] = ((-15, "F-15"), (0, "F0"), (15, "F15"))

BBOX_MODEL_VERSION = "frcnn-v1"
STAGE_MODEL_VERSION = "timelapse-v1"
FABRICATED_MODEL_VERSION = "fabricated-v0"

# Class prior for fabricated ploidy
PLOIDY_PRIOR: tuple[tuple[PloidyClass, float], ...] = (
    (PloidyClass.euploid, 0.60),
    (PloidyClass.aneuploid, 0.30),
    (PloidyClass.mosaic, 0.10),
)
# Class-conditional Beta(a, b) for the ploidy confidence score
PLOIDY_SCORE_BETA: dict[PloidyClass, tuple[float, float]] = {
    PloidyClass.euploid: (8, 2),
    PloidyClass.aneuploid: (7, 3),
    PloidyClass.mosaic: (5, 5),
}
# Live-birth score conditioned on ploidy — euploid skewed positive so ranking is legible
LIVE_BIRTH_BETA: dict[PloidyClass, tuple[float, float]] = {
    PloidyClass.euploid: (6, 4),
    PloidyClass.mosaic: (4, 4),
    PloidyClass.aneuploid: (3, 7),
}

_DATE_RE = re.compile(r"D(\d{4})\.(\d{2})\.(\d{2})")
_WELL_RE = re.compile(r"WELL(\d+)")
_RUN_RE = re.compile(r"RUN(\d+)")


def _embryo_sort_key(label: str) -> int:
    m = re.match(r"Emb(\d+)$", label)
    return int(m.group(1)) if m else 0


def discover_embryos(images_dir: Path) -> list[str]:
    return sorted(
        (p.name for p in images_dir.iterdir() if p.is_dir()),
        key=_embryo_sort_key,
    )


def sorted_run_files(focal_dir: Path) -> list[Path]:
    def key(p: Path) -> int:
        m = _RUN_RE.search(p.name)
        if not m:
            raise ValueError(f"no RUN<int> token in {p.name}")
        return int(m.group(1))

    return sorted(focal_dir.iterdir(), key=key)


def parse_filename_meta(filename: str) -> tuple[date, int]:
    dm = _DATE_RE.search(filename)
    wm = _WELL_RE.search(filename)
    if not dm or not wm:
        raise ValueError(f"could not parse date/well from {filename}")
    return (
        date(int(dm.group(1)), int(dm.group(2)), int(dm.group(3))),
        int(wm.group(1)),
    )


def compute_thumbnail_timepoint(tp_csv: Path) -> int | None:
    with tp_csv.open() as f:
        for row in csv.DictReader(f):
            if row.get("class_name") in BLASTOCYST_STAGES:
                return int(row["timepoint"])
    return None


def seed_images(session: Session, patient: Patient, images_dir: Path) -> int:
    """Insert one row per (embryo, timepoint, focal_depth). Returns row count.

    Asserts F-15, F0, F15 each have `embryo.num_timepoints` frames; fails loudly
    on mismatch per the data-pipeline invariant.
    """
    rows: list[dict] = []
    for embryo in patient.embryos:
        per_depth_counts: dict[int, int] = {}
        for depth_int, depth_str in FOCAL_DEPTHS:
            files = sorted_run_files(images_dir / embryo.label / depth_str)
            per_depth_counts[depth_int] = len(files)
            for tp, fpath in enumerate(files):
                rows.append(
                    {
                        "patient_external_id": patient.external_id,
                        "embryo_label": embryo.label,
                        "timepoint": tp,
                        "focal_depth": depth_int,
                        "path": (
                            f"patients/{patient.external_id}"
                            f"/embryos/{embryo.label}/{depth_str}/{fpath.name}"
                        ),
                    }
                )
        for depth_int, n in per_depth_counts.items():
            if n != embryo.num_timepoints:
                raise ValueError(
                    f"{embryo.label} F{depth_int}: expected "
                    f"{embryo.num_timepoints} frames, got {n}"
                )

    session.execute(insert(Image), rows)
    return len(rows)


def seed_bbox_predictions(
    session: Session,
    patient: Patient,
    bbox_dir: Path,
    model_version: str = BBOX_MODEL_VERSION,
) -> tuple[int, int]:
    """Load Faster-RCNN bbox predictions from per-embryo CSVs.

    Blank corner cells (embryo removed; matches tEmpty in the stage CSV) become
    `bbox = NULL` per data-pipeline rule 3.
    Returns (total_rows, null_rows).
    """
    rows: list[dict] = []
    null_count = 0
    for embryo in patient.embryos:
        csv_path = bbox_dir / f"{embryo.label}_bboxes.csv"
        tps_seen: list[int] = []
        with csv_path.open() as f:
            for row in csv.DictReader(f):
                tp = int(row["timepoint"])
                tps_seen.append(tp)
                ul_str = row["bbox_ul"].strip()
                lr_str = row["bbox_lr"].strip()
                if not ul_str:
                    bbox: BBox | None = None
                    null_count += 1
                else:
                    if not lr_str:
                        raise ValueError(
                            f"{embryo.label} tp={tp}: bbox_ul set but bbox_lr blank"
                        )
                    ul = ast.literal_eval(ul_str)
                    lr = ast.literal_eval(lr_str)
                    bbox = BBox(ul_x=ul[0], ul_y=ul[1], lr_x=lr[0], lr_y=lr[1])
                rows.append(
                    {
                        "patient_external_id": patient.external_id,
                        "embryo_label": embryo.label,
                        "timepoint": tp,
                        "model_version": model_version,
                        "bbox": bbox,
                    }
                )
        if tps_seen != list(range(embryo.num_timepoints)):
            raise ValueError(
                f"{embryo.label} bbox CSV not contiguous 0..{embryo.num_timepoints - 1}"
            )

    session.execute(insert(BboxPrediction), rows)
    return len(rows), null_count


def seed_timepoint_predictions(
    session: Session,
    patient: Patient,
    tp_dir: Path,
    model_version: str = STAGE_MODEL_VERSION,
) -> tuple[int, dict[str, int]]:
    """Load morphokinetic stage predictions from per-embryo CSVs.

    Returns (total_rows, stage_distribution).
    """
    rows: list[dict] = []
    stage_counts: dict[str, int] = {}
    for embryo in patient.embryos:
        csv_path = tp_dir / f"{embryo.label}_postprocessed_timelapse_outputs.csv"
        tps_seen: list[int] = []
        with csv_path.open() as f:
            for row in csv.DictReader(f):
                tp = int(row["timepoint"])
                tps_seen.append(tp)
                stage_name = row["class_name"].strip()
                try:
                    stage = MorphokineticStage(stage_name)
                except ValueError as e:
                    raise ValueError(
                        f"{embryo.label} tp={tp}: unknown stage {stage_name!r}"
                    ) from e
                stage_counts[stage_name] = stage_counts.get(stage_name, 0) + 1
                rows.append(
                    {
                        "patient_external_id": patient.external_id,
                        "embryo_label": embryo.label,
                        "timepoint": tp,
                        "model_version": model_version,
                        "stage": stage,
                    }
                )
        if tps_seen != list(range(embryo.num_timepoints)):
            raise ValueError(
                f"{embryo.label} timepoint CSV not contiguous 0..{embryo.num_timepoints - 1}"
            )

    session.execute(insert(TimepointPrediction), rows)
    return len(rows), stage_counts


def _seed_for(patient_id: str, embryo_label: str) -> int:
    digest = hashlib.sha256(f"{patient_id}:{embryo_label}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def seed_fabricated_predictions(
    session: Session,
    patient: Patient,
    model_version: str = FABRICATED_MODEL_VERSION,
) -> list[tuple[str, PloidyClass, float, float]]:
    """Fabricate ploidy + live-birth predictions, deterministic per (patient, embryo).

    Returns a per-embryo summary `(label, ploidy, ploidy_score, live_birth_score)`.
    """
    classes = [c for c, _ in PLOIDY_PRIOR]
    weights = [w for _, w in PLOIDY_PRIOR]

    ploidy_rows: list[dict] = []
    live_birth_rows: list[dict] = []
    summary: list[tuple[str, PloidyClass, float, float]] = []

    for embryo in patient.embryos:
        rng = random.Random(_seed_for(patient.external_id, embryo.label))
        ploidy = rng.choices(classes, weights=weights)[0]
        p_a, p_b = PLOIDY_SCORE_BETA[ploidy]
        ploidy_score = rng.betavariate(p_a, p_b)
        l_a, l_b = LIVE_BIRTH_BETA[ploidy]
        lb_score = rng.betavariate(l_a, l_b)

        ploidy_rows.append(
            {
                "patient_external_id": patient.external_id,
                "embryo_label": embryo.label,
                "model_version": model_version,
                "ploidy": ploidy,
                "score": ploidy_score,
            }
        )
        live_birth_rows.append(
            {
                "patient_external_id": patient.external_id,
                "embryo_label": embryo.label,
                "model_version": model_version,
                "score": lb_score,
            }
        )
        summary.append((embryo.label, ploidy, ploidy_score, lb_score))

    session.execute(insert(PloidyPrediction), ploidy_rows)
    session.execute(insert(LiveBirthPrediction), live_birth_rows)
    return summary


def seed_patient(session: Session, cfg: dict) -> tuple[Patient, dict[str, int]]:
    """Insert one patient + its embryos + images + real & fabricated predictions
    from its generated tree at data/<external_id>/. Returns (patient, counts)."""
    pdir = DATA_DIR / cfg["external_id"]
    images_dir = pdir / "images"
    bbox_dir = pdir / "predictions" / "bbox"
    tp_dir = pdir / "predictions" / "timepoints"

    patient = Patient(
        external_id=cfg["external_id"],
        name=cfg["name"],
        date_of_birth=cfg["date_of_birth"],
        office=OFFICE,
    )
    session.add(patient)

    for label in discover_embryos(images_dir):
        files = sorted_run_files(images_dir / label / "F0")
        date_seeded, well = parse_filename_meta(files[0].name)
        thumb = compute_thumbnail_timepoint(
            tp_dir / f"{label}_postprocessed_timelapse_outputs.csv"
        )
        patient.embryos.append(
            Embryo(
                label=label,
                num_timepoints=len(files),
                date_seeded=date_seeded,
                well=well,
                thumbnail_timepoint=thumb,
            )
        )
    session.flush()

    image_count = seed_images(session, patient, images_dir)
    bbox_count, bbox_null = seed_bbox_predictions(session, patient, bbox_dir)
    stage_count, _ = seed_timepoint_predictions(session, patient, tp_dir)
    seed_fabricated_predictions(session, patient)
    return patient, {
        "images": image_count,
        "bbox": bbox_count,
        "bbox_null": bbox_null,
        "stages": stage_count,
    }


# Per-embryo run passes for the ledger: (model_version, rows_written, per_tp).
# One run per (embryo, model_version): the two real models + the fabricated one.
def _run_passes(num_timepoints: int) -> tuple[tuple[str, int, bool], ...]:
    return (
        (BBOX_MODEL_VERSION, num_timepoints, True),
        (STAGE_MODEL_VERSION, num_timepoints, True),
        (FABRICATED_MODEL_VERSION, 2, False),  # 1 ploidy + 1 live-birth row
    )


def seed_inference_runs(
    session: Session, patients: list[Patient]
) -> tuple[int, int]:
    """Fabricate the inference_runs ledger: one run per (embryo, model_version),
    with deterministic recent-nightly timestamps. Exactly one run is flagged
    `failed` (resumable nightly failure). Returns (total_runs, failed_runs)."""
    rows: list[dict] = []
    failed = 0
    g = 0  # global embryo index — spreads batches across recent nights
    for patient in patients:
        for embryo in sorted(
            patient.embryos, key=lambda e: _embryo_sort_key(e.label)
        ):
            night = NIGHTLY_ANCHOR - timedelta(days=g % NIGHTS)
            cursor = night + timedelta(minutes=(g // NIGHTS) * 9)
            for model_version, n_rows, per_tp in _run_passes(embryo.num_timepoints):
                tp_start = 0 if per_tp else None
                tp_end = embryo.num_timepoints - 1 if per_tp else None
                rows_written = n_rows
                status = RunStatus.succeeded
                if (patient.external_id, embryo.label, model_version) == FAILED_RUN:
                    # Crashed midway through the sequence; resumable next night.
                    status = RunStatus.failed
                    tp_end = embryo.num_timepoints // 2
                    rows_written = tp_end
                    failed += 1
                duration = timedelta(minutes=max(1, rows_written // 150))
                finished = cursor + duration
                rows.append(
                    {
                        "run_id": f"{model_version}:{patient.external_id}:{embryo.label}",
                        "patient_external_id": patient.external_id,
                        "embryo_label": embryo.label,
                        "model_version": model_version,
                        "tp_start": tp_start,
                        "tp_end": tp_end,
                        "status": status,
                        "rows_written": rows_written,
                        "started_at": cursor,
                        "finished_at": finished,
                    }
                )
                cursor = finished + timedelta(seconds=20)
            g += 1

    session.execute(insert(InferenceRun), rows)
    return len(rows), failed


def seed_evictions(
    session: Session, patients: list[Patient]
) -> list[tuple[str, str, date]]:
    """Stamp `evicted_at` on every image row of the NUM_EVICTED oldest embryos
    (by date_seeded) across the whole roster, simulating disk-pressure eviction
    to cold storage (infra_plan.md §Disk pressure)."""
    all_embryos = [(p, e) for p in patients for e in p.embryos]
    all_embryos.sort(
        key=lambda pe: (
            pe[1].date_seeded,
            pe[0].external_id,
            _embryo_sort_key(pe[1].label),
        )
    )
    evicted: list[tuple[str, str, date]] = []
    for i, (patient, embryo) in enumerate(all_embryos[:NUM_EVICTED]):
        ts = EVICTION_ANCHOR - timedelta(days=i)
        session.execute(
            update(Image)
            .where(
                Image.patient_external_id == patient.external_id,
                Image.embryo_label == embryo.label,
            )
            .values(evicted_at=ts)
        )
        evicted.append((patient.external_id, embryo.label, embryo.date_seeded))
    return evicted


def main() -> None:
    generate(verbose=True)
    roster_ids = [p["external_id"] for p in PATIENTS]

    with Session(engine) as s:
        # Delete every roster patient up front (cascades children), then re-insert.
        s.execute(delete(Patient).where(Patient.external_id.in_(roster_ids)))
        s.flush()

        patients: list[Patient] = []
        totals = {"images": 0, "bbox": 0, "bbox_null": 0, "stages": 0}
        for cfg in PATIENTS:
            patient, counts = seed_patient(s, cfg)
            patients.append(patient)
            for k in totals:
                totals[k] += counts[k]

        run_total, run_failed = seed_inference_runs(s, patients)
        evicted = seed_evictions(s, patients)
        s.commit()

        print()
        total_embryos = 0
        for patient in patients:
            embs = sorted(patient.embryos, key=lambda e: _embryo_sort_key(e.label))
            total_embryos += len(embs)
            labels = " ".join(e.label for e in embs)
            print(
                f"{patient.external_id:<9} {patient.name:<14} "
                f"DOB {patient.date_of_birth}  {len(embs)} embryos  [{labels}]"
            )
        print(
            f"\nSeeded {len(patients)} patients / {total_embryos} embryos "
            f"at {OFFICE}."
        )
        print(
            f"Inserted {totals['images']:,} image rows, "
            f"{totals['bbox']:,} bbox ({totals['bbox_null']:,} NULL), "
            f"{totals['stages']:,} timepoint-stage rows."
        )
        print(
            f"Inference-runs ledger: {run_total} runs "
            f"({run_failed} failed, model versions "
            f"{BBOX_MODEL_VERSION}/{STAGE_MODEL_VERSION}/{FABRICATED_MODEL_VERSION})."
        )
        ev = ", ".join(f"{pid}/{lbl} (seeded {ds})" for pid, lbl, ds in evicted)
        print(f"Evicted {len(evicted)} oldest embryos to cold storage: {ev}")


if __name__ == "__main__":
    main()
