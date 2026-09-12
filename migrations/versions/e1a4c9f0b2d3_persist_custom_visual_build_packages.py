"""Persist immutable custom Canvas build packages in owned storage."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e1a4c9f0b2d3"
down_revision = "c4f0c1a5e201"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("visual_artifact_builds", sa.Column("package_storage_key", sa.String(length=512), nullable=True))
    op.add_column("visual_artifact_builds", sa.Column("package_content_type", sa.String(length=128), nullable=True))
    op.add_column("visual_artifact_builds", sa.Column("manifest_digest", sa.String(length=64), nullable=True))
    op.add_column("visual_artifact_builds", sa.Column("manifest_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

def downgrade():
    op.drop_column("visual_artifact_builds", "manifest_metadata")
    op.drop_column("visual_artifact_builds", "manifest_digest")
    op.drop_column("visual_artifact_builds", "package_content_type")
    op.drop_column("visual_artifact_builds", "package_storage_key")
