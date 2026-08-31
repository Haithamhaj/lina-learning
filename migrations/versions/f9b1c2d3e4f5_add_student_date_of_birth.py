"""Add nullable Parent/System-authoritative Student date of birth."""

import sqlalchemy as sa
from alembic import op


revision = "f9b1c2d3e4f5"
down_revision = "f5a1c2d3e4b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("students", sa.Column("date_of_birth", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("students", "date_of_birth")
