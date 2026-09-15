"""add canonical conversational Concept registry and Segment links

Revision ID: b2c3d4e5f6a7
Revises: fa1b2c3d4e5f
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b2c3d4e5f6a7"
down_revision = "fa1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("learning_segments", sa.Column("conversation_subject_hint", sa.String(length=32), nullable=True))
    op.add_column("learning_segments", sa.Column("primary_concept_ref", sa.String(length=128), nullable=True))
    op.add_column("learning_segments", sa.Column("primary_concept_key", sa.String(length=160), nullable=True))
    op.add_column("learning_segments", sa.Column("concept_registry_version", sa.String(length=64), nullable=True))
    op.add_column("learning_segments", sa.Column("concept_mapping_status", sa.String(length=16), nullable=True))
    op.create_table(
        "canonical_concept_registries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("version", name="uq_canonical_concept_registry_version"),
    )
    op.create_index(
        "uq_canonical_concept_registry_one_active",
        "canonical_concept_registries",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.create_table(
        "learning_segment_concept_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("concept_key", sa.String(length=160), nullable=False),
        sa.Column("broad_subject", sa.String(length=32), nullable=False),
        sa.Column("registry_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["segment_id"], ["learning_segments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("segment_id", "concept_key", name="uq_learning_segment_concept_link"),
    )


def downgrade() -> None:
    op.drop_table("learning_segment_concept_links")
    op.drop_index("uq_canonical_concept_registry_one_active", table_name="canonical_concept_registries")
    op.drop_table("canonical_concept_registries")
    op.drop_column("learning_segments", "concept_mapping_status")
    op.drop_column("learning_segments", "concept_registry_version")
    op.drop_column("learning_segments", "primary_concept_key")
    op.drop_column("learning_segments", "primary_concept_ref")
    op.drop_column("learning_segments", "conversation_subject_hint")
