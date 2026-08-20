"""Add explicit parent/admin and student roles.

Revision ID: 0002_auth_roles
Revises: 0001_foundation_schema
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_auth_roles"
down_revision = "0001_foundation_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Give every local identity a safe student default role."""

    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=32),
            nullable=False,
            server_default="STUDENT",
        ),
    )
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('PARENT_ADMIN', 'STUDENT')",
    )


def downgrade() -> None:
    """Remove the role boundary in reverse dependency order."""

    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")