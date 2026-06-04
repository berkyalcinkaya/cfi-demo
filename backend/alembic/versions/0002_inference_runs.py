"""inference_runs ledger + images.evicted_at

Realizes the demo-facing slice of infra_plan.md: the `inference_runs`
provenance ledger (with a `run_status` enum) and the `images.evicted_at`
eviction marker. Hand-written per docs/database.md — autogenerate mishandles
custom enums.

Revision ID: 0002_inference_runs
Revises: 0001_init
Create Date: 2026-06-04

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_inference_runs"
down_revision: Union[str, None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUN_STATUSES = ("succeeded", "failed", "running")


def upgrade() -> None:
    bind = op.get_bind()

    run_status_enum = postgresql.ENUM(
        *RUN_STATUSES, name="run_status", create_type=False
    )
    run_status_enum.create(bind, checkfirst=False)

    op.create_table(
        "inference_runs",
        sa.Column("run_id", sa.Text(), primary_key=True),
        sa.Column("patient_external_id", sa.Text(), nullable=False),
        sa.Column("embryo_label", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("tp_start", sa.Integer(), nullable=True),
        sa.Column("tp_end", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="run_status", create_type=False),
            nullable=False,
        ),
        sa.Column("rows_written", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_external_id", "embryo_label"],
            ["embryos.patient_external_id", "embryos.label"],
            ondelete="CASCADE",
            name="fk_inference_runs_embryo",
        ),
    )

    op.add_column(
        "images",
        sa.Column("evicted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("images", "evicted_at")
    op.drop_table("inference_runs")

    bind = op.get_bind()
    postgresql.ENUM(name="run_status").drop(bind, checkfirst=False)
