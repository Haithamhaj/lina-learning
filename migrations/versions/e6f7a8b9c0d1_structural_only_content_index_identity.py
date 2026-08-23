"""Allow structural-only content-index identities without semantic enrichment.

Revision ID: e6f7a8b9c0d1
Revises: 9d92f905e25a

Downgrade removes only structural-only derived index rows before restoring the
historical NOT NULL contract. Their preserved structural sources remain
available for a rebuild after re-upgrade; semantic-backed index history is not
changed.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e6f7a8b9c0d1"
down_revision = "9d92f905e25a"
branch_labels = None
depends_on = None


STRUCTURAL_ONLY_INDEX = "uq_content_index_run_structural_identity"


def upgrade() -> None:
    op.alter_column(
        "content_index_runs",
        "semantic_processing_run_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_index(
        STRUCTURAL_ONLY_INDEX,
        "content_index_runs",
        [
            "document_id",
            "structural_processing_run_id",
            "block_schema_version",
            "embedding_route_version",
            "settings_version",
        ],
        unique=True,
        postgresql_where=sa.text("semantic_processing_run_id IS NULL"),
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM content_index_runs WHERE semantic_processing_run_id IS NULL"
    )
    op.drop_index(STRUCTURAL_ONLY_INDEX, table_name="content_index_runs")
    op.alter_column(
        "content_index_runs",
        "semantic_processing_run_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
