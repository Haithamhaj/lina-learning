"""Independent internal Canvas development review records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "a6d9e2f4b7c1"
down_revision = "f4b8d2e9c1a7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("canvas_development_reviews",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        *[sa.Column(name, pg.UUID(as_uuid=True), nullable=False) for name in ("run_id", "studio_runtime_id", "student_id", "learning_session_id")],
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("requested_by", sa.String(120), nullable=False),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("evidence_manifest", pg.JSONB(), nullable=False),
        sa.Column("report", pg.JSONB()),
        sa.Column("ai_execution_id", pg.UUID(as_uuid=True), sa.ForeignKey("ai_executions.id", ondelete="SET NULL")),
        sa.Column("failure_code", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["run_id", "studio_runtime_id", "student_id", "learning_session_id"],
            ["studio_canvas_specialist_runs.id", "studio_canvas_specialist_runs.studio_runtime_id", "studio_canvas_specialist_runs.student_id", "studio_canvas_specialist_runs.learning_session_id"],
            ondelete="CASCADE", name="fk_canvas_dev_review_owned_run"),
        sa.CheckConstraint("status IN ('CAPTURING','READY','RUNNING','COMPLETED','FAILED')", name="ck_canvas_dev_review_status"))
    op.create_index("ix_canvas_dev_review_run_created", "canvas_development_reviews", ["run_id", "created_at"])


def downgrade():
    # Never silently erase saved engineering evidence.
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM canvas_development_reviews)")).scalar():
        raise RuntimeError("Archive development review records before downgrade.")
    op.drop_table("canvas_development_reviews")
