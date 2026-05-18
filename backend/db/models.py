from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    TIMESTAMP,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import REAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.db.enums import MorphokineticStage, PloidyClass
from backend.db.types import BBox, Box

_StageEnum = PGEnum(
    MorphokineticStage,
    name="morphokinetic_stage",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)
_PloidyEnum = PGEnum(
    PloidyClass,
    name="ploidy_class",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)


class Patient(Base):
    __tablename__ = "patients"

    external_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    office: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    embryos: Mapped[list["Embryo"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class Embryo(Base):
    __tablename__ = "embryos"

    patient_external_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("patients.external_id", ondelete="CASCADE"),
        primary_key=True,
    )
    label: Mapped[str] = mapped_column(Text, primary_key=True)
    num_timepoints: Mapped[int] = mapped_column(Integer, nullable=False)
    date_seeded: Mapped[date] = mapped_column(Date, nullable=False)
    well: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_timepoint: Mapped[int | None] = mapped_column(Integer, nullable=True)

    patient: Mapped[Patient] = relationship(back_populates="embryos")
    images: Mapped[list["Image"]] = relationship(
        back_populates="embryo", cascade="all", passive_deletes=True
    )
    bbox_predictions: Mapped[list["BboxPrediction"]] = relationship(
        back_populates="embryo", cascade="all", passive_deletes=True
    )
    timepoint_predictions: Mapped[list["TimepointPrediction"]] = relationship(
        back_populates="embryo", cascade="all", passive_deletes=True
    )
    ploidy_predictions: Mapped[list["PloidyPrediction"]] = relationship(
        back_populates="embryo", cascade="all", passive_deletes=True
    )
    live_birth_predictions: Mapped[list["LiveBirthPrediction"]] = relationship(
        back_populates="embryo", cascade="all", passive_deletes=True
    )


class Image(Base):
    __tablename__ = "images"

    patient_external_id: Mapped[str] = mapped_column(Text, primary_key=True)
    embryo_label: Mapped[str] = mapped_column(Text, primary_key=True)
    timepoint: Mapped[int] = mapped_column(Integer, primary_key=True)
    focal_depth: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)

    embryo: Mapped[Embryo] = relationship(back_populates="images")

    __table_args__ = (
        ForeignKeyConstraint(
            ["patient_external_id", "embryo_label"],
            ["embryos.patient_external_id", "embryos.label"],
            ondelete="CASCADE",
            name="fk_images_embryo",
        ),
    )


class BboxPrediction(Base):
    __tablename__ = "bbox_predictions"

    patient_external_id: Mapped[str] = mapped_column(Text, primary_key=True)
    embryo_label: Mapped[str] = mapped_column(Text, primary_key=True)
    timepoint: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_version: Mapped[str] = mapped_column(Text, primary_key=True)
    bbox: Mapped[BBox | None] = mapped_column(Box(), nullable=True)

    embryo: Mapped[Embryo] = relationship(back_populates="bbox_predictions")

    __table_args__ = (
        ForeignKeyConstraint(
            ["patient_external_id", "embryo_label"],
            ["embryos.patient_external_id", "embryos.label"],
            ondelete="CASCADE",
            name="fk_bbox_embryo",
        ),
    )


class TimepointPrediction(Base):
    __tablename__ = "timepoint_predictions"

    patient_external_id: Mapped[str] = mapped_column(Text, primary_key=True)
    embryo_label: Mapped[str] = mapped_column(Text, primary_key=True)
    timepoint: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_version: Mapped[str] = mapped_column(Text, primary_key=True)
    stage: Mapped[MorphokineticStage] = mapped_column(_StageEnum, nullable=False)

    embryo: Mapped[Embryo] = relationship(back_populates="timepoint_predictions")

    __table_args__ = (
        ForeignKeyConstraint(
            ["patient_external_id", "embryo_label"],
            ["embryos.patient_external_id", "embryos.label"],
            ondelete="CASCADE",
            name="fk_tp_embryo",
        ),
    )


class PloidyPrediction(Base):
    __tablename__ = "ploidy_predictions"

    patient_external_id: Mapped[str] = mapped_column(Text, primary_key=True)
    embryo_label: Mapped[str] = mapped_column(Text, primary_key=True)
    model_version: Mapped[str] = mapped_column(Text, primary_key=True)
    predicted_at: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    ploidy: Mapped[PloidyClass] = mapped_column(_PloidyEnum, nullable=False)
    score: Mapped[float] = mapped_column(REAL, nullable=False)

    embryo: Mapped[Embryo] = relationship(back_populates="ploidy_predictions")

    __table_args__ = (
        ForeignKeyConstraint(
            ["patient_external_id", "embryo_label"],
            ["embryos.patient_external_id", "embryos.label"],
            ondelete="CASCADE",
            name="fk_ploidy_embryo",
        ),
        CheckConstraint("score >= 0 AND score <= 1", name="ck_ploidy_score_range"),
    )


class LiveBirthPrediction(Base):
    __tablename__ = "live_birth_predictions"

    patient_external_id: Mapped[str] = mapped_column(Text, primary_key=True)
    embryo_label: Mapped[str] = mapped_column(Text, primary_key=True)
    model_version: Mapped[str] = mapped_column(Text, primary_key=True)
    predicted_at: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    score: Mapped[float] = mapped_column(REAL, nullable=False)

    embryo: Mapped[Embryo] = relationship(back_populates="live_birth_predictions")

    __table_args__ = (
        ForeignKeyConstraint(
            ["patient_external_id", "embryo_label"],
            ["embryos.patient_external_id", "embryos.label"],
            ondelete="CASCADE",
            name="fk_live_birth_embryo",
        ),
        CheckConstraint("score >= 0 AND score <= 1", name="ck_live_birth_score_range"),
    )
