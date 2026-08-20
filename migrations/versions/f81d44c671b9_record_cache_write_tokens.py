"""Record GPT-5.6 prompt cache-write tokens in the AI execution ledger.

Revision ID: f81d44c671b9
Revises: e42b31d687a8
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "f81d44c671b9"
down_revision = "e42b31d687a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_executions", sa.Column("cache_write_tokens", sa.SmallInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_executions", "cache_write_tokens")
