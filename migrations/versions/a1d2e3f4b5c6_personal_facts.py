"""Add source-grounded Personal Facts persistence."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "a1d2e3f4b5c6"
down_revision = "f9b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "personal_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("fact_key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.String(length=256), nullable=False),
        sa.Column("display_statement", sa.Text(), nullable=False),
        sa.Column("support_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("support_count >= 0", name="ck_personal_facts_support_count_nonnegative"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("student_id", "category", "fact_key", "value", name="uq_personal_facts_identity"),
        sa.UniqueConstraint("id", "student_id", name="uq_personal_facts_id_student"),
    )
    op.create_index("ix_personal_facts_student_key_latest", "personal_facts", ["student_id", "fact_key", "last_observed_at", "id"])
    op.create_index("ix_personal_facts_student_category", "personal_facts", ["student_id", "category"])

    op.create_table(
        "personal_fact_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("personal_fact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("normalized_assertion", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_message_id"], ["learning_messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_session_id"], ["learning_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["personal_fact_id", "student_id"],
            ["personal_facts.id", "personal_facts.student_id"],
            ondelete="CASCADE",
            name="fk_personal_fact_observations_fact_student",
        ),
        sa.UniqueConstraint("personal_fact_id", "source_message_id", name="uq_personal_fact_observation_source"),
    )
    op.create_index("ix_personal_fact_observations_fact_observed", "personal_fact_observations", ["personal_fact_id", "observed_at", "id"])

    op.create_table(
        "personal_fact_extraction_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("ai_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=128), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_metadata", postgresql.JSONB(), nullable=True),
        sa.CheckConstraint("status IN ('PENDING', 'RUNNING', 'COMPLETED', 'SKIPPED_CAPACITY')", name="ck_personal_fact_extraction_runs_status"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["learning_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ai_execution_id"], ["ai_executions.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("student_id", "session_id", name="uq_personal_fact_extraction_runs_student_session"),
        sa.UniqueConstraint("job_id", name="uq_personal_fact_extraction_runs_job"),
    )
    op.create_index("ix_personal_fact_extraction_runs_student_status", "personal_fact_extraction_runs", ["student_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_personal_fact_extraction_runs_student_status", table_name="personal_fact_extraction_runs")
    op.drop_table("personal_fact_extraction_runs")
    op.drop_index("ix_personal_fact_observations_fact_observed", table_name="personal_fact_observations")
    op.drop_table("personal_fact_observations")
    op.drop_index("ix_personal_facts_student_category", table_name="personal_facts")
    op.drop_index("ix_personal_facts_student_key_latest", table_name="personal_facts")
    op.drop_table("personal_facts")
