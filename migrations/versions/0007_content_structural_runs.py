"""Make Docling structural runs idempotent and retain processing failures.

Revision ID: 0007_content_structural_runs
Revises: 0006_content_foundation
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_content_structural_runs"
down_revision = "0006_content_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("content_processing_runs", sa.Column("failure_detail", sa.Text(), nullable=True))
    op.create_unique_constraint(
        "uq_content_processing_run_version",
        "content_processing_runs",
        ["document_id", "kind", "processor_version"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_content_processing_run_version", "content_processing_runs", type_="unique")
    op.drop_column("content_processing_runs", "failure_detail")
