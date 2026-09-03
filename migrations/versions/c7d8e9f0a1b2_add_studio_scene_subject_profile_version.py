"""Add exact Subject Capability profile lineage to Studio Scenes."""

from alembic import op
import sqlalchemy as sa


revision = "c7d8e9f0a1b2"
down_revision = "b6e4c2a9d7f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "studio_scenes",
        sa.Column("subject_profile_version", sa.String(length=64), nullable=False, server_default="subject-profile-v1"),
    )
    op.alter_column("studio_scenes", "subject_profile_version", server_default=None)
    op.add_column("studio_events", sa.Column("action_key", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("studio_events", "action_key")
    op.drop_column("studio_scenes", "subject_profile_version")
