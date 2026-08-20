"""Add the PostgreSQL-backed jobs and worker foundation.

Revision ID: 0003_jobs_worker_foundation
Revises: 0002_auth_roles
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_jobs_worker_foundation"
down_revision = "0002_auth_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create durable job lifecycle storage and database idempotency."""

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "attempt_count",
            sa.SmallInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "max_attempts",
            sa.SmallInteger(),
            nullable=False,
            server_default="3",
        ),
        sa.Column(
            "run_after",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("claimed_by", sa.String(length=128), nullable=True),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_jobs_attempt_count_nonnegative"),
        sa.CheckConstraint("max_attempts > 0", name="ck_jobs_max_attempts_positive"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_jobs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_jobs_claimable",
        "jobs",
        ["status", "run_after"],
    )
    op.create_index(
        "uq_jobs_type_idempotency_key",
        "jobs",
        ["job_type", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    """Remove the jobs foundation without touching raw learner data."""

    op.drop_index("uq_jobs_type_idempotency_key", table_name="jobs")
    op.drop_index("ix_jobs_claimable", table_name="jobs")
    op.drop_table("jobs")
