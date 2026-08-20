"""Create the Phase 0 PostgreSQL foundation.

Revision ID: 0001_foundation_schema
Revises:
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_foundation_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable vector support and create identity/grade foundation tables."""

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "identity_provider",
            sa.String(length=64),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("external_subject", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "identity_provider",
            "external_subject",
            name="uq_users_identity",
        ),
    )

    op.create_table(
        "students",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_students_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_students_user_id"),
    )

    op.create_table(
        "parent_student_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "relationship_type",
            sa.String(length=64),
            nullable=False,
            server_default="parent",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_user_id"],
            ["users.id"],
            name="fk_parent_student_relationships_parent_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name="fk_parent_student_relationships_student_id_students",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "parent_user_id",
            "student_id",
            name="uq_parent_student_relationship",
        ),
    )
    op.create_index(
        "ix_parent_student_relationships_student_id",
        "parent_student_relationships",
        ["student_id"],
    )

    op.create_table(
        "grade_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("grade_level", sa.SmallInteger(), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "grade_level BETWEEN 1 AND 12",
            name="ck_grade_periods_grade_level",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name="fk_grade_periods_student_id_students",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "student_id",
            "starts_on",
            name="uq_grade_periods_student_start",
        ),
    )
    op.create_index(
        "ix_grade_periods_student_active",
        "grade_periods",
        ["student_id", "is_active"],
    )


def downgrade() -> None:
    """Remove the foundation in dependency order."""

    op.drop_index(
        "ix_grade_periods_student_active",
        table_name="grade_periods",
    )
    op.drop_table("grade_periods")
    op.drop_index(
        "ix_parent_student_relationships_student_id",
        table_name="parent_student_relationships",
    )
    op.drop_table("parent_student_relationships")
    op.drop_table("students")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")