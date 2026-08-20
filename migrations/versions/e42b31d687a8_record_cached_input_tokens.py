"""Record cached input tokens separately in the AI execution ledger.

Revision ID: e42b31d687a8
Revises: 4f3f83db9c50
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "e42b31d687a8"
down_revision = "4f3f83db9c50"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_executions", sa.Column("cached_input_tokens", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_executions", "cached_input_tokens")
