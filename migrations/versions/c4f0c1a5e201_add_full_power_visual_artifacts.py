"""Add immutable Full-Power Canvas artifact registry and build history.

Revision ID: c4f0c1a5e201
Revises: 9b6e2c4d8f01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "c4f0c1a5e201"
down_revision = "9b6e2c4d8f01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visual_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stable_slug", sa.String(length=96), nullable=False),
        sa.Column("semantic_purpose", sa.String(length=600), nullable=False),
        sa.Column("runtime_kind", sa.String(length=64), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=16), nullable=False, server_default="CANDIDATE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("stable_slug", name="uq_visual_artifacts_stable_slug"),
        sa.CheckConstraint("lifecycle_status IN ('CANDIDATE', 'VALIDATED', 'TRUSTED', 'RETIRED')", name="ck_visual_artifacts_lifecycle"),
    )
    op.create_index("ix_visual_artifacts_lifecycle_runtime", "visual_artifacts", ["lifecycle_status", "runtime_kind"])
    op.create_table(
        "visual_artifact_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("visual_artifacts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("parent_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("visual_artifact_versions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_digest", sa.String(length=64), nullable=False),
        sa.Column("runtime_contract_version", sa.String(length=64), nullable=False),
        sa.Column("parameter_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("manifest_contract", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("dependency_capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("definition_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation_status", sa.String(length=16), nullable=False, server_default="CANDIDATE"),
        sa.Column("technical_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("artifact_id", "version_number", name="uq_visual_artifact_versions_number"),
        sa.UniqueConstraint("source_digest", name="uq_visual_artifact_versions_source_digest"),
        sa.CheckConstraint("version_number > 0", name="ck_visual_artifact_versions_positive"),
        sa.CheckConstraint("validation_status IN ('CANDIDATE', 'VALIDATED', 'TRUSTED', 'RETIRED')", name="ck_visual_artifact_versions_validation"),
    )
    op.create_index("ix_visual_artifact_versions_artifact", "visual_artifact_versions", ["artifact_id", "version_number"])
    op.create_table(
        "visual_artifact_builds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("visual_artifact_versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("source_digest", sa.String(length=64), nullable=False),
        sa.Column("bundle_digest", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("technical_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('VALIDATED', 'FAILED', 'PREVIEWED')", name="ck_visual_artifact_builds_status"),
    )
    op.create_index("ix_visual_artifact_builds_version_created", "visual_artifact_builds", ["artifact_version_id", "created_at"])
    op.create_table(
        "visual_artifact_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("visual_artifact_versions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("studio_scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("studio_scenes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bound_parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("semantic_manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("current_semantic_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("locale", sa.String(length=16), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("studio_scene_id", name="uq_visual_artifact_instances_scene"),
    )
    op.create_index("ix_visual_artifact_instances_student_created", "visual_artifact_instances", ["student_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_visual_artifact_instances_student_created", table_name="visual_artifact_instances")
    op.drop_table("visual_artifact_instances")
    op.drop_index("ix_visual_artifact_builds_version_created", table_name="visual_artifact_builds")
    op.drop_table("visual_artifact_builds")
    op.drop_index("ix_visual_artifact_versions_artifact", table_name="visual_artifact_versions")
    op.drop_table("visual_artifact_versions")
    op.drop_index("ix_visual_artifacts_lifecycle_runtime", table_name="visual_artifacts")
    op.drop_table("visual_artifacts")
