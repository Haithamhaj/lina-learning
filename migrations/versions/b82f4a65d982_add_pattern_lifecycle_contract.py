"""Add deterministic Pattern lifecycle provenance.

Revision ID: b82f4a65d982
Revises: d64a70c4cf81
"""

from alembic import op
import sqlalchemy as sa


revision = "b82f4a65d982"
down_revision = "d64a70c4cf81"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("learner_patterns", sa.Column("scope_key", sa.String(length=256), nullable=True))
    op.add_column("learner_patterns", sa.Column("policy_version", sa.String(length=64), nullable=True))
    op.add_column("learner_patterns", sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("learner_patterns", sa.Column("cycle_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("learner_patterns", sa.Column("last_supported_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("learner_patterns", sa.Column("last_challenged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("learner_patterns", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("""
        UPDATE learner_patterns
        SET scope_key = md5(id::text),
            policy_version = 'legacy-pattern-policy-v0',
            first_detected_at = now(),
            cycle_started_at = now()
    """)
    op.alter_column("learner_patterns", "scope_key", nullable=False, server_default="legacy")
    op.alter_column("learner_patterns", "policy_version", nullable=False, server_default="legacy-pattern-policy-v0")
    op.alter_column("learner_patterns", "first_detected_at", nullable=False, server_default=sa.text("now()"))
    op.alter_column("learner_patterns", "cycle_started_at", nullable=False, server_default=sa.text("now()"))
    op.drop_constraint("uq_learner_pattern_scope", "learner_patterns", type_="unique")
    op.create_unique_constraint(
        "uq_learner_pattern_scope",
        "learner_patterns",
        ["student_id", "policy_version", "pattern_type", "pattern_key", "scope_key"],
    )

    op.add_column("pattern_evidence", sa.Column("relationship", sa.String(length=32), nullable=True))
    op.add_column("pattern_evidence", sa.Column("processing_run_id", sa.UUID(), nullable=True))
    op.add_column("pattern_evidence", sa.Column("policy_version", sa.String(length=64), nullable=True))
    op.add_column("pattern_evidence", sa.Column("task_ref", sa.String(length=128), nullable=True))
    op.add_column("pattern_evidence", sa.Column("context_ref", sa.String(length=128), nullable=True))
    op.add_column("pattern_evidence", sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("""
        UPDATE pattern_evidence AS link
        SET relationship = 'supports',
            processing_run_id = pattern.processing_run_id,
            policy_version = 'legacy-pattern-policy-v0',
            task_ref = 'legacy',
            context_ref = 'legacy',
            observed_at = now()
        FROM learner_patterns AS pattern
        WHERE pattern.id = link.pattern_id
    """)
    op.alter_column("pattern_evidence", "relationship", nullable=False, server_default="supports")
    op.alter_column("pattern_evidence", "policy_version", nullable=False, server_default="legacy-pattern-policy-v0")
    op.alter_column("pattern_evidence", "task_ref", nullable=False, server_default="legacy")
    op.alter_column("pattern_evidence", "context_ref", nullable=False, server_default="legacy")
    op.alter_column("pattern_evidence", "observed_at", nullable=False, server_default=sa.text("now()"))
    op.create_foreign_key(
        "fk_pattern_evidence_processing_run",
        "pattern_evidence",
        "intelligence_processing_runs",
        ["processing_run_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_pattern_evidence_processing_run", "pattern_evidence", type_="foreignkey")
    op.drop_column("pattern_evidence", "observed_at")
    op.drop_column("pattern_evidence", "policy_version")
    op.drop_column("pattern_evidence", "context_ref")
    op.drop_column("pattern_evidence", "task_ref")
    op.drop_column("pattern_evidence", "processing_run_id")
    op.drop_column("pattern_evidence", "relationship")
    op.drop_constraint("uq_learner_pattern_scope", "learner_patterns", type_="unique")
    op.create_unique_constraint(
        "uq_learner_pattern_scope",
        "learner_patterns",
        ["student_id", "processing_run_id", "pattern_type", "pattern_key", "scope"],
    )
    op.drop_column("learner_patterns", "resolved_at")
    op.drop_column("learner_patterns", "last_challenged_at")
    op.drop_column("learner_patterns", "last_supported_at")
    op.drop_column("learner_patterns", "cycle_started_at")
    op.drop_column("learner_patterns", "first_detected_at")
    op.drop_column("learner_patterns", "policy_version")
    op.drop_column("learner_patterns", "scope_key")
