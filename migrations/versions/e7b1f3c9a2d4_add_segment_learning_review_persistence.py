"""Add SEG-EVID-01A Segment closure and review persistence contracts.

Revision ID: e7b1f3c9a2d4
Revises: 1e94c7b8a2d6

This migration stores only durable closure, review, and provenance contracts.
It intentionally does not infer historical Segments or semantic findings.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e7b1f3c9a2d4"
down_revision = "1e94c7b8a2d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("learning_segments", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("learning_segments", sa.Column("closure_reason", sa.String(length=32), nullable=True))
    op.create_check_constraint(
        "ck_learning_segments_closure_state",
        "learning_segments",
        "(closed_at IS NULL AND closure_reason IS NULL) OR "
        "(closed_at IS NOT NULL AND closure_reason IS NOT NULL AND "
        "closure_reason IN ('NEXT_SEGMENT_CREATED', 'SESSION_CLOSED'))",
    )

    op.create_table(
        "segment_learning_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=128), nullable=False),
        sa.Column("rubric_version", sa.String(length=64), nullable=False),
        sa.Column("review_policy_version", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="PENDING", nullable=False),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_segment_learning_reviews_status",
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["segment_id"], ["learning_segments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ai_execution_id"], ["ai_executions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "segment_id",
            "schema_version",
            "prompt_version",
            "rubric_version",
            "review_policy_version",
            "provider",
            "model",
            name="uq_segment_learning_review_identity",
        ),
    )
    op.create_index("ix_segment_learning_reviews_session", "segment_learning_reviews", ["session_id"])
    op.create_index("ix_segment_learning_reviews_student", "segment_learning_reviews", ["student_id"])
    op.create_index("ix_segment_learning_reviews_status", "segment_learning_reviews", ["status"])

    op.add_column("learning_events", sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("learning_events", sa.Column("segment_review_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "learning_events",
        sa.Column(
            "candidate_event_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "learning_events",
        sa.Column(
            "source_message_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_foreign_key(
        "fk_learning_events_segment",
        "learning_events",
        "learning_segments",
        ["segment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_learning_events_segment_review",
        "learning_events",
        "segment_learning_reviews",
        ["segment_review_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute(
        "UPDATE learning_events SET "
        "candidate_event_ids = jsonb_build_array(candidate_event_id::text), "
        "source_message_ids = CASE "
        "WHEN source_message_id IS NULL THEN '[]'::jsonb "
        "ELSE jsonb_build_array(source_message_id::text) END"
    )
    op.drop_constraint("learning_events_candidate_event_id_fkey", "learning_events", type_="foreignkey")
    op.alter_column(
        "learning_events",
        "candidate_event_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_foreign_key(
        "fk_learning_events_candidate_event_id",
        "learning_events",
        "candidate_events",
        ["candidate_event_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_candidate_free_event = connection.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM learning_events WHERE candidate_event_id IS NULL)")
    ).scalar_one()
    if has_candidate_free_event:
        raise RuntimeError(
            "Cannot downgrade SEG-EVID-01A while learning_events contains candidate_event_id NULL. "
            "The legacy schema cannot represent Candidate-free Events."
        )

    op.drop_constraint("fk_learning_events_candidate_event_id", "learning_events", type_="foreignkey")
    op.alter_column(
        "learning_events",
        "candidate_event_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_foreign_key(
        "learning_events_candidate_event_id_fkey",
        "learning_events",
        "candidate_events",
        ["candidate_event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint("fk_learning_events_segment_review", "learning_events", type_="foreignkey")
    op.drop_constraint("fk_learning_events_segment", "learning_events", type_="foreignkey")
    op.drop_column("learning_events", "source_message_ids")
    op.drop_column("learning_events", "candidate_event_ids")
    op.drop_column("learning_events", "segment_review_id")
    op.drop_column("learning_events", "segment_id")

    op.drop_index("ix_segment_learning_reviews_status", table_name="segment_learning_reviews")
    op.drop_index("ix_segment_learning_reviews_student", table_name="segment_learning_reviews")
    op.drop_index("ix_segment_learning_reviews_session", table_name="segment_learning_reviews")
    op.drop_table("segment_learning_reviews")

    op.drop_constraint("ck_learning_segments_closure_state", "learning_segments", type_="check")
    op.drop_column("learning_segments", "closure_reason")
    op.drop_column("learning_segments", "closed_at")
