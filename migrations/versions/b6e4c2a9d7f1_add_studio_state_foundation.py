"""Add durable, subject-agnostic Studio state foundation.

Revision ID: b6e4c2a9d7f1
Revises: a1d2e3f4b5c6
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "b6e4c2a9d7f1"
down_revision = "a1d2e3f4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_learning_sessions_id_student",
        "learning_sessions",
        ["id", "student_id"],
    )
    op.create_unique_constraint(
        "uq_learning_segments_id_session",
        "learning_segments",
        ["id", "session_id"],
    )
    op.create_unique_constraint(
        "uq_learning_messages_id_session",
        "learning_messages",
        ["id", "session_id"],
    )
    op.create_table(
        "studio_runtimes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learning_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("active_segment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="OPEN"),
        sa.Column("latest_event_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_tutor_observation_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["learning_session_id", "student_id"],
            ["learning_sessions.id", "learning_sessions.student_id"],
            ondelete="CASCADE",
            name="fk_studio_runtimes_session_student",
        ),
        sa.ForeignKeyConstraint(
            ["active_segment_id", "learning_session_id"],
            ["learning_segments.id", "learning_segments.session_id"],
            ondelete="RESTRICT",
            name="fk_studio_runtimes_active_segment_session",
        ),
        sa.UniqueConstraint("learning_session_id", name="uq_studio_runtimes_learning_session"),
        sa.UniqueConstraint("id", "student_id", name="uq_studio_runtimes_id_student"),
        sa.UniqueConstraint(
            "id",
            "student_id",
            "learning_session_id",
            name="uq_studio_runtimes_id_student_session",
        ),
        sa.CheckConstraint("status IN ('OPEN', 'CLOSED', 'ARCHIVED')", name="ck_studio_runtimes_status"),
        sa.CheckConstraint("latest_event_sequence >= 0", name="ck_studio_runtimes_latest_event_sequence_nonnegative"),
        sa.CheckConstraint("last_tutor_observation_sequence >= 0", name="ck_studio_runtimes_tutor_watermark_nonnegative"),
        sa.CheckConstraint("last_tutor_observation_sequence <= latest_event_sequence", name="ck_studio_runtimes_tutor_watermark_bounded"),
    )
    op.create_index("ix_studio_runtimes_student_status", "studio_runtimes", ["student_id", "status"])

    op.create_table(
        "studio_scenes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("studio_runtime_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learning_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_segment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subject_key", sa.String(length=64), nullable=False),
        sa.Column("concept_keys", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("activity_key", sa.String(length=128), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("renderer_key", sa.String(length=128), nullable=False),
        sa.Column("renderer_version", sa.String(length=64), nullable=False),
        sa.Column("activity_contract_version", sa.String(length=64), nullable=False),
        sa.Column("payload_schema_version", sa.String(length=64), nullable=False),
        sa.Column("scene_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ACCEPTED"),
        sa.Column("seed_payload", postgresql.JSONB(), nullable=False),
        sa.Column("accessibility_payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="en"),
        sa.Column("direction", sa.String(length=8), nullable=False, server_default="auto"),
        sa.Column("source_asset_refs", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["studio_runtime_id", "student_id", "learning_session_id"],
            [
                "studio_runtimes.id",
                "studio_runtimes.student_id",
                "studio_runtimes.learning_session_id",
            ],
            ondelete="CASCADE",
            name="fk_studio_scenes_runtime_session_student",
        ),
        sa.ForeignKeyConstraint(
            ["source_segment_id", "learning_session_id"],
            ["learning_segments.id", "learning_segments.session_id"],
            ondelete="RESTRICT",
            name="fk_studio_scenes_source_segment_session",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id", "learning_session_id"],
            ["learning_messages.id", "learning_messages.session_id"],
            ondelete="RESTRICT",
            name="fk_studio_scenes_source_message_session",
        ),
        sa.UniqueConstraint("id", "studio_runtime_id", "student_id", name="uq_studio_scenes_id_runtime_student"),
        sa.CheckConstraint("status IN ('ACCEPTED', 'ACTIVE', 'SUPERSEDED', 'ARCHIVED')", name="ck_studio_scenes_status"),
        sa.CheckConstraint("scene_version >= 0", name="ck_studio_scenes_version_nonnegative"),
        sa.CheckConstraint("direction IN ('ltr', 'rtl', 'auto')", name="ck_studio_scenes_direction"),
    )
    op.create_index("ix_studio_scenes_runtime_status", "studio_scenes", ["studio_runtime_id", "status"])
    op.create_index("uq_studio_scenes_runtime_active", "studio_scenes", ["studio_runtime_id"], unique=True, postgresql_where=sa.text("status = 'ACTIVE'"))

    op.create_table(
        "studio_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("studio_runtime_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learning_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=32), nullable=False),
        sa.Column("event_kind", sa.String(length=128), nullable=False),
        sa.Column("event_schema_version", sa.String(length=64), nullable=False),
        sa.Column("subject_key", sa.String(length=64), nullable=True),
        sa.Column("activity_key", sa.String(length=128), nullable=True),
        sa.Column("source_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("base_scene_version", sa.Integer(), nullable=True),
        sa.Column("resulting_scene_version", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("command_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("causal_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload_schema_version", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("result_status", sa.String(length=32), nullable=False, server_default="ACCEPTED"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("persisted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["studio_runtime_id", "student_id", "learning_session_id"],
            [
                "studio_runtimes.id",
                "studio_runtimes.student_id",
                "studio_runtimes.learning_session_id",
            ],
            ondelete="CASCADE",
            name="fk_studio_events_runtime_session_student",
        ),
        sa.ForeignKeyConstraint(
            ["segment_id", "learning_session_id"],
            ["learning_segments.id", "learning_segments.session_id"],
            ondelete="RESTRICT",
            name="fk_studio_events_segment_session",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id", "learning_session_id"],
            ["learning_messages.id", "learning_messages.session_id"],
            ondelete="RESTRICT",
            name="fk_studio_events_source_message_session",
        ),
        sa.ForeignKeyConstraint(
            ["causal_event_id", "studio_runtime_id", "student_id"],
            ["studio_events.id", "studio_events.studio_runtime_id", "studio_events.student_id"],
            ondelete="RESTRICT",
            name="fk_studio_events_causal_runtime_student",
        ),
        sa.ForeignKeyConstraint(
            ["scene_id", "studio_runtime_id", "student_id"],
            ["studio_scenes.id", "studio_scenes.studio_runtime_id", "studio_scenes.student_id"],
            ondelete="RESTRICT", name="fk_studio_events_scene_runtime_student",
        ),
        sa.UniqueConstraint("studio_runtime_id", "sequence", name="uq_studio_events_runtime_sequence"),
        sa.UniqueConstraint("id", "studio_runtime_id", "student_id", name="uq_studio_events_id_runtime_student"),
        sa.CheckConstraint("sequence > 0", name="ck_studio_events_sequence_positive"),
        sa.CheckConstraint("actor IN ('STUDENT', 'TUTOR', 'SYSTEM', 'CANVAS_SPECIALIST')", name="ck_studio_events_actor"),
        sa.CheckConstraint("(scene_id IS NULL AND base_scene_version IS NULL AND resulting_scene_version IS NULL) OR (scene_id IS NOT NULL AND base_scene_version >= 0 AND resulting_scene_version = base_scene_version + 1)", name="ck_studio_events_scene_versions"),
        sa.CheckConstraint("result_status IN ('ACCEPTED')", name="ck_studio_events_result_status"),
    )
    op.create_index("ix_studio_events_runtime_sequence", "studio_events", ["studio_runtime_id", "sequence"])
    op.create_index("ix_studio_events_scene_sequence", "studio_events", ["scene_id", "sequence"])
    op.create_index("ix_studio_events_runtime_since_tutor_watermark", "studio_events", ["studio_runtime_id", "sequence"])
    op.create_index("uq_studio_events_runtime_idempotency_key", "studio_events", ["studio_runtime_id", "idempotency_key"], unique=True, postgresql_where=sa.text("idempotency_key IS NOT NULL"))

    op.create_table(
        "studio_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("studio_runtime_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_schema_version", sa.String(length=64), nullable=False),
        sa.Column("latest_event_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_scene_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_scene_version", sa.Integer(), nullable=True),
        sa.Column("active_subject_key", sa.String(length=64), nullable=True),
        sa.Column("active_activity_key", sa.String(length=128), nullable=True),
        sa.Column("active_step_key", sa.String(length=128), nullable=True),
        sa.Column("last_meaningful_student_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("state_payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["studio_runtime_id", "student_id"], ["studio_runtimes.id", "studio_runtimes.student_id"],
            ondelete="CASCADE", name="fk_studio_snapshots_runtime_student",
        ),
        sa.ForeignKeyConstraint(
            ["current_scene_id", "studio_runtime_id", "student_id"],
            ["studio_scenes.id", "studio_scenes.studio_runtime_id", "studio_scenes.student_id"],
            ondelete="RESTRICT", name="fk_studio_snapshots_scene_runtime_student",
        ),
        sa.ForeignKeyConstraint(
            ["last_meaningful_student_event_id", "studio_runtime_id", "student_id"],
            ["studio_events.id", "studio_events.studio_runtime_id", "studio_events.student_id"],
            ondelete="RESTRICT", name="fk_studio_snapshots_student_event_runtime_student",
        ),
        sa.UniqueConstraint("studio_runtime_id", name="uq_studio_snapshots_runtime"),
        sa.CheckConstraint("latest_event_sequence >= 0", name="ck_studio_snapshots_latest_sequence_nonnegative"),
        sa.CheckConstraint("current_scene_version IS NULL OR current_scene_version >= 0", name="ck_studio_snapshots_current_scene_version_nonnegative"),
    )

    op.create_table(
        "studio_student_interactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("studio_runtime_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learning_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interaction_kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("context_payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("tutor_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ai_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tutor_message_id"], ["learning_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ai_execution_id"], ["ai_executions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["studio_runtime_id", "student_id", "learning_session_id"],
            [
                "studio_runtimes.id",
                "studio_runtimes.student_id",
                "studio_runtimes.learning_session_id",
            ],
            ondelete="CASCADE",
            name="fk_studio_interactions_runtime_session_student",
        ),
        sa.ForeignKeyConstraint(
            ["source_event_id", "studio_runtime_id", "student_id"],
            ["studio_events.id", "studio_events.studio_runtime_id", "studio_events.student_id"],
            ondelete="CASCADE", name="fk_studio_interactions_event_runtime_student",
        ),
        sa.UniqueConstraint("source_event_id", name="uq_studio_student_interactions_source_event"),
        sa.UniqueConstraint("id", "studio_runtime_id", "student_id", name="uq_studio_interactions_id_runtime_student"),
        sa.CheckConstraint("status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', 'SUPERSEDED')", name="ck_studio_interactions_status"),
    )
    op.create_index("ix_studio_interactions_pending", "studio_student_interactions", ["studio_runtime_id", "status", "created_at"])

    op.create_table(
        "studio_tutor_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("studio_runtime_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_event_sequence", sa.Integer(), nullable=False),
        sa.Column("through_event_sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="SELECTED"),
        sa.Column("student_interaction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ai_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("failure_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ai_execution_id"], ["ai_executions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["studio_runtime_id", "student_id"], ["studio_runtimes.id", "studio_runtimes.student_id"],
            ondelete="CASCADE", name="fk_studio_observations_runtime_student",
        ),
        sa.ForeignKeyConstraint(
            ["student_interaction_id", "studio_runtime_id", "student_id"],
            ["studio_student_interactions.id", "studio_student_interactions.studio_runtime_id", "studio_student_interactions.student_id"],
            ondelete="RESTRICT", name="fk_studio_observations_interaction_runtime_student",
        ),
        sa.CheckConstraint("status IN ('SELECTED', 'COMMITTED', 'FAILED', 'CANCELLED', 'SUPERSEDED')", name="ck_studio_observations_status"),
        sa.CheckConstraint("from_event_sequence > 0 AND through_event_sequence >= from_event_sequence", name="ck_studio_observations_sequence_range"),
    )
    op.create_index("ix_studio_observations_runtime_created", "studio_tutor_observations", ["studio_runtime_id", "created_at"])
    op.create_index("ix_studio_observations_execution_runtime", "studio_tutor_observations", ["ai_execution_id", "studio_runtime_id"])

    op.create_table(
        "studio_canvas_specialist_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("studio_runtime_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learning_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("base_scene_version", sa.Integer(), nullable=False),
        sa.Column("subject_key", sa.String(length=64), nullable=False),
        sa.Column("capability_profile_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ai_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("output_schema_version", sa.String(length=64), nullable=False),
        sa.Column("accepted_scene_version", sa.Integer(), nullable=True),
        sa.Column("failure_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ai_execution_id"], ["ai_executions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["studio_runtime_id", "student_id", "learning_session_id"],
            [
                "studio_runtimes.id",
                "studio_runtimes.student_id",
                "studio_runtimes.learning_session_id",
            ],
            ondelete="CASCADE",
            name="fk_studio_specialist_runs_runtime_session_student",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id", "learning_session_id"],
            ["learning_messages.id", "learning_messages.session_id"],
            ondelete="RESTRICT",
            name="fk_studio_specialist_runs_source_message_session",
        ),
        sa.ForeignKeyConstraint(
            ["scene_id", "studio_runtime_id", "student_id"],
            ["studio_scenes.id", "studio_scenes.studio_runtime_id", "studio_scenes.student_id"],
            ondelete="RESTRICT", name="fk_studio_specialist_runs_scene_runtime_student",
        ),
        sa.CheckConstraint("status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', 'SUPERSEDED', 'REJECTED')", name="ck_studio_specialist_runs_status"),
        sa.CheckConstraint("base_scene_version >= 0", name="ck_studio_specialist_runs_base_scene_version"),
        sa.CheckConstraint("accepted_scene_version IS NULL OR accepted_scene_version >= 0", name="ck_studio_specialist_runs_accepted_scene_version"),
    )
    op.create_index("ix_studio_specialist_runs_runtime_status", "studio_canvas_specialist_runs", ["studio_runtime_id", "status", "created_at"])
    op.create_index("ix_studio_specialist_runs_runtime_source_message", "studio_canvas_specialist_runs", ["studio_runtime_id", "source_message_id"])


def downgrade() -> None:
    op.drop_index("ix_studio_specialist_runs_runtime_source_message", table_name="studio_canvas_specialist_runs")
    op.drop_index("ix_studio_specialist_runs_runtime_status", table_name="studio_canvas_specialist_runs")
    op.drop_table("studio_canvas_specialist_runs")
    op.drop_index("ix_studio_observations_execution_runtime", table_name="studio_tutor_observations")
    op.drop_index("ix_studio_observations_runtime_created", table_name="studio_tutor_observations")
    op.drop_table("studio_tutor_observations")
    op.drop_index("ix_studio_interactions_pending", table_name="studio_student_interactions")
    op.drop_table("studio_student_interactions")
    op.drop_table("studio_snapshots")
    op.drop_index("uq_studio_events_runtime_idempotency_key", table_name="studio_events")
    op.drop_index("ix_studio_events_runtime_since_tutor_watermark", table_name="studio_events")
    op.drop_index("ix_studio_events_scene_sequence", table_name="studio_events")
    op.drop_index("ix_studio_events_runtime_sequence", table_name="studio_events")
    op.drop_table("studio_events")
    op.drop_index("uq_studio_scenes_runtime_active", table_name="studio_scenes")
    op.drop_index("ix_studio_scenes_runtime_status", table_name="studio_scenes")
    op.drop_table("studio_scenes")
    op.drop_index("ix_studio_runtimes_student_status", table_name="studio_runtimes")
    op.drop_table("studio_runtimes")
    op.drop_constraint("uq_learning_messages_id_session", "learning_messages", type_="unique")
    op.drop_constraint("uq_learning_segments_id_session", "learning_segments", type_="unique")
    op.drop_constraint("uq_learning_sessions_id_student", "learning_sessions", type_="unique")
