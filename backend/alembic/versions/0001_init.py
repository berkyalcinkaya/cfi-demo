"""initial schema

Revision ID: 0001_init
Revises:
Create Date: 2026-05-13

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType

revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class _Box(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw) -> str:
        return "box"


MORPHOKINETIC_STAGES = (
    "t1", "tPN", "tPNf", "t2", "t3", "t4", "t5", "t6", "t7", "t8",
    "tM", "tB", "tEB", "tEmpty",
)
PLOIDY_CLASSES = ("euploid", "aneuploid", "mosaic")


def upgrade() -> None:
    bind = op.get_bind()

    stage_enum = postgresql.ENUM(
        *MORPHOKINETIC_STAGES, name="morphokinetic_stage", create_type=False,
    )
    stage_enum.create(bind, checkfirst=False)

    ploidy_enum = postgresql.ENUM(
        *PLOIDY_CLASSES, name="ploidy_class", create_type=False,
    )
    ploidy_enum.create(bind, checkfirst=False)

    op.create_table(
        "patients",
        sa.Column("external_id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("office", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "embryos",
        sa.Column(
            "patient_external_id",
            sa.Text(),
            sa.ForeignKey("patients.external_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("label", sa.Text(), primary_key=True),
        sa.Column("num_timepoints", sa.Integer(), nullable=False),
        sa.Column("date_seeded", sa.Date(), nullable=False),
        sa.Column("well", sa.Integer(), nullable=True),
        sa.Column("thumbnail_timepoint", sa.Integer(), nullable=True),
    )

    op.create_table(
        "images",
        sa.Column("patient_external_id", sa.Text(), primary_key=True),
        sa.Column("embryo_label", sa.Text(), primary_key=True),
        sa.Column("timepoint", sa.Integer(), primary_key=True),
        sa.Column("focal_depth", sa.Integer(), primary_key=True),
        sa.Column("path", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_external_id", "embryo_label"],
            ["embryos.patient_external_id", "embryos.label"],
            ondelete="CASCADE",
            name="fk_images_embryo",
        ),
    )

    op.create_table(
        "bbox_predictions",
        sa.Column("patient_external_id", sa.Text(), primary_key=True),
        sa.Column("embryo_label", sa.Text(), primary_key=True),
        sa.Column("timepoint", sa.Integer(), primary_key=True),
        sa.Column("model_version", sa.Text(), primary_key=True),
        sa.Column("bbox", _Box(), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_external_id", "embryo_label"],
            ["embryos.patient_external_id", "embryos.label"],
            ondelete="CASCADE",
            name="fk_bbox_embryo",
        ),
    )

    op.create_table(
        "timepoint_predictions",
        sa.Column("patient_external_id", sa.Text(), primary_key=True),
        sa.Column("embryo_label", sa.Text(), primary_key=True),
        sa.Column("timepoint", sa.Integer(), primary_key=True),
        sa.Column("model_version", sa.Text(), primary_key=True),
        sa.Column(
            "stage",
            postgresql.ENUM(name="morphokinetic_stage", create_type=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["patient_external_id", "embryo_label"],
            ["embryos.patient_external_id", "embryos.label"],
            ondelete="CASCADE",
            name="fk_tp_embryo",
        ),
    )

    op.create_table(
        "ploidy_predictions",
        sa.Column("patient_external_id", sa.Text(), primary_key=True),
        sa.Column("embryo_label", sa.Text(), primary_key=True),
        sa.Column("model_version", sa.Text(), primary_key=True),
        sa.Column(
            "predicted_at",
            sa.Date(),
            nullable=False,
            server_default=sa.text("CURRENT_DATE"),
        ),
        sa.Column(
            "ploidy",
            postgresql.ENUM(name="ploidy_class", create_type=False),
            nullable=False,
        ),
        sa.Column("score", postgresql.REAL(), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_external_id", "embryo_label"],
            ["embryos.patient_external_id", "embryos.label"],
            ondelete="CASCADE",
            name="fk_ploidy_embryo",
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 1", name="ck_ploidy_score_range"
        ),
    )

    op.create_table(
        "live_birth_predictions",
        sa.Column("patient_external_id", sa.Text(), primary_key=True),
        sa.Column("embryo_label", sa.Text(), primary_key=True),
        sa.Column("model_version", sa.Text(), primary_key=True),
        sa.Column(
            "predicted_at",
            sa.Date(),
            nullable=False,
            server_default=sa.text("CURRENT_DATE"),
        ),
        sa.Column("score", postgresql.REAL(), nullable=False),
        sa.ForeignKeyConstraint(
            ["patient_external_id", "embryo_label"],
            ["embryos.patient_external_id", "embryos.label"],
            ondelete="CASCADE",
            name="fk_live_birth_embryo",
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 1", name="ck_live_birth_score_range"
        ),
    )


def downgrade() -> None:
    op.drop_table("live_birth_predictions")
    op.drop_table("ploidy_predictions")
    op.drop_table("timepoint_predictions")
    op.drop_table("bbox_predictions")
    op.drop_table("images")
    op.drop_table("embryos")
    op.drop_table("patients")

    bind = op.get_bind()
    postgresql.ENUM(name="ploidy_class").drop(bind, checkfirst=False)
    postgresql.ENUM(name="morphokinetic_stage").drop(bind, checkfirst=False)
