"""Step 2: seed one patient + 10 embryos from data/patient1/.

Re-runnable: deletes the existing patient row (cascading children) before inserting.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import random
import re
from datetime import date
from pathlib import Path

from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from backend.db.enums import MorphokineticStage, PloidyClass
from backend.db.models import (
    BboxPrediction,
    Embryo,
    Image,
    LiveBirthPrediction,
    Patient,
    PloidyPrediction,
    TimepointPrediction,
)
from backend.db.session import engine
from backend.db.types import BBox

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "patient1"

PATIENT_SEED = {
    "external_id": "patient1",
    "name": "Jane Cooper",
    "date_of_birth": date(1990, 7, 22),
    "office": "Carolina's Fertility Clinic",
}

BLASTOCYST_STAGES = {"tB", "tEB"}

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


def main() -> None:
    images_dir = DATA_DIR / "images"
    bbox_dir = DATA_DIR / "predictions" / "bbox"
    tp_dir = DATA_DIR / "predictions" / "timepoints"

    embryo_labels = discover_embryos(images_dir)
    if len(embryo_labels) != 10:
        print(f"warning: expected 10 embryos, found {len(embryo_labels)}")

    with Session(engine) as s:
        s.execute(
            delete(Patient).where(Patient.external_id == PATIENT_SEED["external_id"])
        )
        s.flush()

        patient = Patient(**PATIENT_SEED)
        s.add(patient)

        for label in embryo_labels:
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

        s.flush()
        image_count = seed_images(s, patient, images_dir)
        bbox_count, bbox_null = seed_bbox_predictions(s, patient, bbox_dir)
        stage_count, stage_dist = seed_timepoint_predictions(s, patient, tp_dir)
        fab_summary = seed_fabricated_predictions(s, patient)
        s.commit()

        print(
            f"Seeded {patient.external_id} — {patient.name}, "
            f"DOB {patient.date_of_birth}, {patient.office}"
        )
        total_tp = 0
        for e in sorted(patient.embryos, key=lambda x: _embryo_sort_key(x.label)):
            total_tp += e.num_timepoints
            thumb = (
                f"thumb_tp={e.thumbnail_timepoint}"
                if e.thumbnail_timepoint is not None
                else "thumb_tp=NULL"
            )
            print(
                f"  {e.label:<6}  K={e.num_timepoints:<5}  "
                f"seeded={e.date_seeded}  well={e.well}  {thumb}"
            )
        print(
            f"Inserted {image_count:,} image rows "
            f"({total_tp:,} timepoints × {len(FOCAL_DEPTHS)} focal depths)."
        )
        print(
            f"Inserted {bbox_count:,} bbox rows "
            f"({bbox_null:,} NULL, model={BBOX_MODEL_VERSION})."
        )
        print(
            f"Inserted {stage_count:,} timepoint-stage rows "
            f"(model={STAGE_MODEL_VERSION})."
        )
        stage_parts = [
            f"{s.value}={stage_dist.get(s.value, 0):,}"
            for s in MorphokineticStage
            if stage_dist.get(s.value, 0) > 0
        ]
        print(f"  stage distribution: {', '.join(stage_parts)}")

        print(
            f"\nFabricated {len(fab_summary)} ploidy + live-birth predictions "
            f"(model={FABRICATED_MODEL_VERSION}); ranked by live-birth score:"
        )
        for label, ploidy, p_score, lb in sorted(
            fab_summary, key=lambda r: r[3], reverse=True
        ):
            print(
                f"  {label:<6}  ploidy={ploidy.value:<10}({p_score:.2f})  "
                f"live_birth={lb:.2f}"
            )


if __name__ == "__main__":
    main()
