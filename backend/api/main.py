from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.schemas import (
    BBoxOut,
    EmbryoCardOut,
    FocalImageOut,
    FocalStackResponse,
    MilestoneOut,
    PatientResponse,
    PloidyOut,
    PredictionOut,
    ThumbnailOut,
    TimelinePointOut,
    TimelineResponse,
)
from backend.db.models import (
    BboxPrediction,
    Embryo,
    Image,
    LiveBirthPrediction,
    Patient,
    PloidyPrediction,
    TimepointPrediction,
)
from backend.db.session import SessionLocal
from backend.db.types import BBox

DATA_DIR = (Path(__file__).resolve().parents[2] / "data").resolve()
ALLOWED_IMAGE_EXTS = {".jpeg", ".jpg", ".png"}
FABRICATED_PREFIX = "fabricated-"

app = FastAPI(title="Embpred Demo API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_session() -> Iterator[Session]:
    with SessionLocal() as s:
        yield s


def _compute_age(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    return (today.year - dob.year) - ((today.month, today.day) < (dob.month, dob.day))


def _image_url(s3_key: str) -> str:
    # patients/{patient}/embryos/{embryo}/{depth}/{file} -> /images/{patient}/{embryo}/{depth}/{file}
    parts = s3_key.split("/")
    return f"/images/{parts[1]}/{parts[3]}/{parts[4]}/{parts[5]}"


def _bbox_out(b: BBox | None) -> BBoxOut | None:
    if b is None:
        return None
    return BBoxOut(ul_x=b.ul_x, ul_y=b.ul_y, lr_x=b.lr_x, lr_y=b.lr_y)


def _is_fab(model_version: str) -> bool:
    return model_version.startswith(FABRICATED_PREFIX)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: str, s: Session = Depends(get_session)) -> PatientResponse:
    patient = s.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(404, f"patient {patient_id!r} not found")

    cards: list[EmbryoCardOut] = []
    for e in patient.embryos:
        thumbnail: ThumbnailOut | None = None
        if e.thumbnail_timepoint is not None:
            img = s.execute(
                select(Image).where(
                    Image.patient_external_id == e.patient_external_id,
                    Image.embryo_label == e.label,
                    Image.timepoint == e.thumbnail_timepoint,
                    Image.focal_depth == 0,
                )
            ).scalar_one_or_none()
            if img is not None:
                thumbnail = ThumbnailOut(
                    timepoint=e.thumbnail_timepoint,
                    url=_image_url(img.path),
                )

        ploidy_out: PloidyOut | None = None
        if e.ploidy_predictions:
            p = e.ploidy_predictions[0]
            ploidy_out = PloidyOut(
                ploidy=p.ploidy.value,
                score=p.score,
                model_version=p.model_version,
                is_fabricated=_is_fab(p.model_version),
            )

        lb_out: PredictionOut | None = None
        if e.live_birth_predictions:
            lb = e.live_birth_predictions[0]
            lb_out = PredictionOut(
                score=lb.score,
                model_version=lb.model_version,
                is_fabricated=_is_fab(lb.model_version),
            )

        cards.append(
            EmbryoCardOut(
                label=e.label,
                num_timepoints=e.num_timepoints,
                date_seeded=e.date_seeded,
                well=e.well,
                thumbnail=thumbnail,
                ploidy=ploidy_out,
                live_birth=lb_out,
            )
        )

    cards.sort(
        key=lambda c: (c.live_birth is None, -(c.live_birth.score if c.live_birth else 0))
    )

    return PatientResponse(
        id=patient.external_id,
        name=patient.name,
        date_of_birth=patient.date_of_birth,
        age=_compute_age(patient.date_of_birth),
        office=patient.office,
        embryos=cards,
    )


@app.get(
    "/patients/{patient_id}/embryos/{embryo_label}/timepoints/{timepoint}",
    response_model=FocalStackResponse,
)
def get_focal_stack(
    patient_id: str,
    embryo_label: str,
    timepoint: int,
    s: Session = Depends(get_session),
) -> FocalStackResponse:
    embryo = s.execute(
        select(Embryo).where(
            Embryo.patient_external_id == patient_id, Embryo.label == embryo_label
        )
    ).scalar_one_or_none()
    if embryo is None:
        raise HTTPException(404, f"embryo {embryo_label!r} not found")
    if not (0 <= timepoint < embryo.num_timepoints):
        raise HTTPException(
            404, f"timepoint {timepoint} out of range [0, {embryo.num_timepoints})"
        )

    images = (
        s.execute(
            select(Image)
            .where(
                Image.patient_external_id == patient_id,
                Image.embryo_label == embryo_label,
                Image.timepoint == timepoint,
            )
            .order_by(Image.focal_depth)
        )
        .scalars()
        .all()
    )

    bbox_row = s.execute(
        select(BboxPrediction).where(
            BboxPrediction.patient_external_id == patient_id,
            BboxPrediction.embryo_label == embryo_label,
            BboxPrediction.timepoint == timepoint,
        )
    ).scalar_one_or_none()

    stage_row = s.execute(
        select(TimepointPrediction).where(
            TimepointPrediction.patient_external_id == patient_id,
            TimepointPrediction.embryo_label == embryo_label,
            TimepointPrediction.timepoint == timepoint,
        )
    ).scalar_one_or_none()

    return FocalStackResponse(
        patient_id=patient_id,
        embryo=embryo_label,
        timepoint=timepoint,
        num_timepoints=embryo.num_timepoints,
        stage=stage_row.stage.value if stage_row else None,
        bbox=_bbox_out(bbox_row.bbox) if bbox_row else None,
        focal_stack=[
            FocalImageOut(focal_depth=i.focal_depth, url=_image_url(i.path))
            for i in images
        ],
    )


@app.get(
    "/patients/{patient_id}/embryos/{embryo_label}/timeline",
    response_model=TimelineResponse,
)
def get_timeline(
    patient_id: str,
    embryo_label: str,
    s: Session = Depends(get_session),
) -> TimelineResponse:
    embryo = s.execute(
        select(Embryo).where(
            Embryo.patient_external_id == patient_id, Embryo.label == embryo_label
        )
    ).scalar_one_or_none()
    if embryo is None:
        raise HTTPException(404, f"embryo {embryo_label!r} not found")

    stream_rows = (
        s.execute(
            select(TimepointPrediction.timepoint, TimepointPrediction.stage)
            .where(
                TimepointPrediction.patient_external_id == patient_id,
                TimepointPrediction.embryo_label == embryo_label,
            )
            .order_by(TimepointPrediction.timepoint)
        )
        .all()
    )

    first_seen: dict[str, int] = {}
    counts: dict[str, int] = {}
    stream: list[TimelinePointOut] = []
    for tp, stage in stream_rows:
        name = stage.value
        if name not in first_seen:
            first_seen[name] = tp
        counts[name] = counts.get(name, 0) + 1
        stream.append(TimelinePointOut(timepoint=tp, stage=name))

    milestones = [
        MilestoneOut(stage=name, first_seen=first_seen[name], frames_at_stage=counts[name])
        for name in sorted(first_seen, key=lambda n: first_seen[n])
    ]

    return TimelineResponse(
        patient_id=patient_id,
        embryo=embryo_label,
        num_timepoints=embryo.num_timepoints,
        stream=stream,
        milestones=milestones,
    )


@app.get("/images/{patient_id}/{embryo_label}/{focal_dir}/{filename}")
def get_image(patient_id: str, embryo_label: str, focal_dir: str, filename: str):
    if Path(filename).suffix.lower() not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(400, "unsupported file extension")
    candidate = (
        DATA_DIR / patient_id / "images" / embryo_label / focal_dir / filename
    ).resolve()
    try:
        candidate.relative_to(DATA_DIR)
    except ValueError:
        raise HTTPException(400, "invalid path")
    if not candidate.is_file():
        raise HTTPException(404, "image not found")
    return FileResponse(candidate)
