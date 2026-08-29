"""Widen AI execution usage and latency metrics to PostgreSQL INTEGER.

Revision ID: f5a1c2d3e4b6
Revises: d7c3b9a5e1f2

Real provider executions can legitimately exceed the signed SMALLINT range in
both token usage and elapsed milliseconds. Upgrade preserves every existing
value. Downgrade is allowed only while every value still fits the old schema,
so no operational ledger row can be truncated or corrupted silently.
"""

import sqlalchemy as sa
from alembic import op

revision = "f5a1c2d3e4b6"
down_revision = "d7c3b9a5e1f2"
branch_labels = None
depends_on = None


_METRIC_COLUMNS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_tokens",
    "output_tokens",
    "latency_ms",
)


def upgrade() -> None:
    for column_name in _METRIC_COLUMNS:
        op.alter_column(
            "ai_executions",
            column_name,
            existing_type=sa.SmallInteger(),
            type_=sa.Integer(),
            postgresql_using=f"{column_name}::integer",
            existing_nullable=column_name != "latency_ms",
        )


def downgrade() -> None:
    connection = op.get_bind()
    out_of_range = " OR ".join(
        f"{column_name} < -32768 OR {column_name} > 32767"
        for column_name in _METRIC_COLUMNS
    )
    if connection.execute(
        sa.text(f"SELECT EXISTS (SELECT 1 FROM ai_executions WHERE {out_of_range})")
    ).scalar_one():
        raise RuntimeError(
            "Cannot downgrade AI execution metrics to SMALLINT while ledger values "
            "outside the signed SMALLINT range exist."
        )

    for column_name in _METRIC_COLUMNS:
        op.alter_column(
            "ai_executions",
            column_name,
            existing_type=sa.Integer(),
            type_=sa.SmallInteger(),
            postgresql_using=f"{column_name}::smallint",
            existing_nullable=column_name != "latency_ms",
        )
