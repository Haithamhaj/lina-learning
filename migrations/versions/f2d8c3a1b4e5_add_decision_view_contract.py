"""add versioned deterministic decision view contract

Revision ID: f2d8c3a1b4e5
Revises: c91f6b7e43a1
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f2d8c3a1b4e5"
down_revision = "c91f6b7e43a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_decision_view_run_concept", "decision_views", type_="unique")
    op.add_column("decision_views", sa.Column("subject", sa.String(length=32), server_default="UNKNOWN", nullable=False))
    op.add_column("decision_views", sa.Column("view_type", sa.String(length=64), server_default="learning_status", nullable=False))
    op.add_column("decision_views", sa.Column("conclusion", sa.String(length=32), server_default="INSUFFICIENT_EVIDENCE", nullable=False))
    op.add_column("decision_views", sa.Column("confidence", sa.String(length=16), server_default="LOW", nullable=False))
    op.add_column("decision_views", sa.Column("explanation", sa.Text(), server_default="", nullable=False))
    op.add_column("decision_views", sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False))
    op.add_column("decision_views", sa.Column("state_ids", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False))
    op.add_column("decision_views", sa.Column("pattern_ids", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False))
    op.add_column("decision_views", sa.Column("source_versions", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False))
    op.add_column("decision_views", sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
    op.create_unique_constraint(
        "uq_decision_view_scope_version",
        "decision_views",
        ["student_id", "processing_run_id", "subject", "concept_ref", "view_type", "policy_version"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_decision_view_scope_version", "decision_views", type_="unique")
    op.drop_column("decision_views", "generated_at")
    op.drop_column("decision_views", "source_versions")
    op.drop_column("decision_views", "pattern_ids")
    op.drop_column("decision_views", "state_ids")
    op.drop_column("decision_views", "evidence_ids")
    op.drop_column("decision_views", "explanation")
    op.drop_column("decision_views", "confidence")
    op.drop_column("decision_views", "conclusion")
    op.drop_column("decision_views", "view_type")
    op.drop_column("decision_views", "subject")
    op.create_unique_constraint("uq_decision_view_run_concept", "decision_views", ["student_id", "processing_run_id", "concept_ref"])
