"""keep reprocess job identity without a queue retention dependency

Revision ID: c51e8fa3b923
Revises: b40d7ea2f812
Create Date: 2026-08-22
"""

from alembic import op


revision = "c51e8fa3b923"
down_revision = "b40d7ea2f812"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("intelligence_reprocess_runs_job_id_fkey", "intelligence_reprocess_runs", type_="foreignkey")


def downgrade() -> None:
    op.create_foreign_key(
        "intelligence_reprocess_runs_job_id_fkey",
        "intelligence_reprocess_runs",
        "jobs",
        ["job_id"],
        ["id"],
        ondelete="SET NULL",
    )
