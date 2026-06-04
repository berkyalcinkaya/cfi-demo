from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class BBoxOut(BaseModel):
    ul_x: int
    ul_y: int
    lr_x: int
    lr_y: int


class PredictionOut(BaseModel):
    score: float
    model_version: str
    is_fabricated: bool


class PloidyOut(PredictionOut):
    ploidy: str  # euploid | aneuploid | mosaic


class ThumbnailOut(BaseModel):
    timepoint: int
    url: str


class EmbryoCardOut(BaseModel):
    label: str
    num_timepoints: int
    date_seeded: date
    well: int | None
    thumbnail: ThumbnailOut | None
    ploidy: PloidyOut | None
    live_birth: PredictionOut | None


class PatientResponse(BaseModel):
    id: str
    name: str
    date_of_birth: date
    age: int
    office: str
    embryos: list[EmbryoCardOut]


class PatientSummaryOut(BaseModel):
    """Lightweight row for the sidebar patient selector."""

    id: str
    name: str
    age: int
    num_embryos: int


class FocalImageOut(BaseModel):
    focal_depth: int
    url: str


class FocalStackResponse(BaseModel):
    patient_id: str
    embryo: str
    timepoint: int
    num_timepoints: int
    stage: str | None
    bbox: BBoxOut | None
    focal_stack: list[FocalImageOut]


class TimelinePointOut(BaseModel):
    timepoint: int
    stage: str


class MilestoneOut(BaseModel):
    stage: str
    first_seen: int
    frames_at_stage: int


class TimelineResponse(BaseModel):
    patient_id: str
    embryo: str
    num_timepoints: int
    stream: list[TimelinePointOut]
    milestones: list[MilestoneOut]


class ComparisonEmbryoOut(BaseModel):
    """One embryo's morphokinetic timeline for the stacked comparison view.

    Ordered by live-birth rank by the endpoint; ploidy is the raw class
    (folding mosaic -> aneuploid happens client-side at display time).
    """

    label: str
    num_timepoints: int
    ploidy: str | None
    live_birth_score: float | None
    stream: list[TimelinePointOut]
    milestones: list[MilestoneOut]


class ComparisonResponse(BaseModel):
    patient_id: str
    embryos: list[ComparisonEmbryoOut]


# --- Admin panel (read-only views over the fabricated infra tables) ---


class IngestRunOut(BaseModel):
    """One row of the `inference_runs` ledger for the admin ingest log."""

    run_id: str
    patient_external_id: str
    embryo_label: str
    model_version: str
    tp_start: int | None
    tp_end: int | None
    status: str  # succeeded | failed | running
    rows_written: int
    started_at: datetime
    finished_at: datetime | None
    is_fabricated: bool


class EvictedEmbryoOut(BaseModel):
    """An embryo with ≥1 image evicted to cold storage (images.evicted_at)."""

    patient_external_id: str
    patient_name: str
    embryo_label: str
    evicted_at: datetime  # most recent eviction across the embryo's images
    num_images: int
    source_hint: str
