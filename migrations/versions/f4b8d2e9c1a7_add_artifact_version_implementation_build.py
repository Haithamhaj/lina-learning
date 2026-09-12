"""Reference the immutable implementation Build from reusable artifact versions."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f4b8d2e9c1a7"
down_revision = "e1a4c9f0b2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("visual_artifact_versions", sa.Column("implementation_build_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_visual_artifact_versions_implementation_build", "visual_artifact_versions", "visual_artifact_builds", ["implementation_build_id"], ["id"], ondelete="RESTRICT")


def downgrade() -> None:
    op.drop_constraint("fk_visual_artifact_versions_implementation_build", "visual_artifact_versions", type_="foreignkey")
    op.drop_column("visual_artifact_versions", "implementation_build_id")
