"""Rename the configurable restricted-sexual-content boundary.

Revision ID: eb52c7a1f4d9
Revises: a4d8e2f6b1c3
Create Date: 2026-08-26
"""

from alembic import op


revision = "eb52c7a1f4d9"
down_revision = "a4d8e2f6b1c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SafetyAudit is deliberately untouched: its historical category remains
    # authoritative audit provenance. The unique configuration row simply gets
    # the clearer current policy identifier.
    op.execute(
        "UPDATE student_topic_boundaries "
        "SET category = 'SEXUAL_CONTENT' "
        "WHERE category = 'HUMAN_REPRODUCTION'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE student_topic_boundaries "
        "SET category = 'HUMAN_REPRODUCTION' "
        "WHERE category = 'SEXUAL_CONTENT'"
    )
