from __future__ import annotations

from datetime import date

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
