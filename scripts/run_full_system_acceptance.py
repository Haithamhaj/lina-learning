"""Prepare and run Lina's isolated full-system acceptance journey.

The default mode is a provider-disabled, no-write preflight. Database URLs are
resolved only from explicitly named process environment variables. Database
cloning and real-model reconstruction require separate explicit flags, while
credentials stay out of command arguments, errors, and generated artifacts.
"""

# This standalone tool intentionally bootstraps the repository root before
# importing project modules.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from alembic.util.exc import CommandError
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.consolidation import EVIDENCE_RUBRIC_VERSION
from services.intelligence.segment_reviews import (
    SEGMENT_LEARNING_REVIEW_PROMPT_VERSION,
    SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
    SEGMENT_REVIEW_POLICY_VERSION,
)
from services.model_gateway.factory import create_segment_evidence_gateway
from services.model_gateway.gateway import (
    AIExecutionLineage,
    ModelGateway,
)
from services.model_gateway.openai_provider import OpenAIResponsesProvider
from services.platform.config import Settings
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    AIExecution,
    CurrentLearningState,
    DecisionView,
    IntelligenceProcessingRun,
    IntelligenceSessionAuthority,
    Job,
    JobStatus,
    LearnerIntelligenceCard,
    LearnerPattern,
    LearningEvent,
    LearningEvidence,
    LearningMessage,
    LearningSegment,
    LearningSession,
    ModelTask,
    SegmentLearningReview,
)
from services.tutor.segment_lifecycle import (
    SEGMENT_LEARNING_REVIEW_JOB,
    is_segment_structurally_reviewable,
    reconcile_segments_for_session_close,
)
from services.tutor.session_lifecycle import (
    SESSION_FINALIZATION_PIPELINE,
    SESSION_INTELLIGENCE_FINALIZE_JOB,
    SessionLifecyclePolicy,
    close_session_if_eligible,
    enqueue_session_intelligence_finalization_if_ready,
)
from workers.intelligence_handlers import register_intelligence_handlers
from workers.job_worker import JobHandlerRegistry, run_once

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_SESSION_ID = UUID("8b1b647c-91ec-427e-b455-0adbca831101")
ACCEPTANCE_RECONSTRUCTION_VERSION = "acceptance-segment-reconstruction-v1"
ACCEPTANCE_RECONSTRUCTION_OPERATION = "full_system_acceptance_segment_reconstruction"
HISTORICAL_ACCEPTANCE_OPERATION = "full_system_historical_intelligence_acceptance"
ACCEPTANCE_PIPELINE = "segment-finalization-v1"
CANONICAL_TEST_DATABASE_NAME = "lina_learning_test"
DEFAULT_SOURCE_DATABASE_ENV_VAR = "LINA_ACCEPTANCE_SOURCE_DATABASE_URL"
DEFAULT_TARGET_DATABASE_ENV_VAR = "LINA_ACCEPTANCE_TARGET_DATABASE_URL"
ACCEPTANCE_MODEL_TIMEOUT_ENV_VAR = "LINA_ACCEPTANCE_MODEL_TIMEOUT_SECONDS"
DEFAULT_ACCEPTANCE_MODEL_TIMEOUT_SECONDS = 120.0
MIN_ACCEPTANCE_MODEL_TIMEOUT_SECONDS = 30
MAX_ACCEPTANCE_MODEL_TIMEOUT_SECONDS = 300
_SAFE_CHILD_ENVIRONMENT_KEYS = (
    "PATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TMPDIR",
    "SYSTEMROOT",
)


class AcceptanceSafetyError(RuntimeError):
    """Fail-closed operator error whose detail is safe to display."""


class ReconstructionValidationError(AcceptanceSafetyError):
    """The provider output does not exactly cover ordered source Messages."""


@dataclass(frozen=True)
class HistoricalCounts:
    messages: int
    student_messages: int
    tutor_messages: int
    candidates: int


@dataclass(frozen=True)
class HistoricalSnapshot:
    counts: HistoricalCounts
    raw_message_manifest_sha256: str


EXPECTED_HISTORICAL_COUNTS = HistoricalCounts(
    messages=145,
    student_messages=73,
    tutor_messages=72,
    candidates=38,
)


@dataclass(frozen=True)
class DatabaseIdentity:
    host: str
    port: int
    database: str

    @property
    def safe_label(self) -> str:
        return f"{self.host}:{self.port}/{self.database}"


@dataclass(frozen=True)
class DatabaseBoundary:
    source_identity: DatabaseIdentity
    target_identity: DatabaseIdentity
    source_url: URL = field(repr=False)
    target_url: URL = field(repr=False)


@dataclass(frozen=True)
class CommandSpec:
    purpose: str
    argv: tuple[str, ...]
    environment: dict[str, str] = field(repr=False)
    working_directory: Path = ROOT


@dataclass(frozen=True)
class SourceMessage:
    id: UUID
    role: str
    content: str = field(repr=False)
    created_at: datetime
    metadata: object = field(default_factory=dict, repr=False)
    ai_execution_id: UUID | None = None


@dataclass(frozen=True)
class AcceptanceConfiguration:
    source_database_url: str = field(repr=False)
    target_database_url: str = field(repr=False)
    artifact_directory: Path
    execute_reconstruction: bool = False


@dataclass(frozen=True)
class AuditStage:
    pending_json_path: Path
    final_json_path: Path
    final_markdown_path: Path


@dataclass(frozen=True)
class ResumeTargetState:
    intelligence_pipeline: str
    segment_count: int
    assigned_message_count: int
    pending_audit_exists: bool
    committed_audit_exists: bool


class ReconstructionAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: UUID
    segment_sequence: int = Field(..., ge=1, le=145)
    boundary_reason: str | None = Field(..., min_length=1, max_length=400)


class ReconstructionEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[ACCEPTANCE_RECONSTRUCTION_VERSION]
    assignments: list[ReconstructionAssignment] = Field(
        ..., min_length=1, max_length=145
    )


RECONSTRUCTION_RESPONSE_SCHEMA: dict[str, object] = {
    "name": "acceptance_segment_reconstruction_v1",
    "schema": ReconstructionEnvelope.model_json_schema(),
}


def canonical_database_identity(database_url: str) -> DatabaseIdentity:
    """Return the credential-free PostgreSQL server/database identity."""

    try:
        parsed = make_url(database_url)
    except (ArgumentError, TypeError, ValueError):
        raise AcceptanceSafetyError(
            "Database URL is invalid; credentials were not displayed."
        ) from None
    if parsed.get_backend_name() != "postgresql":
        raise AcceptanceSafetyError(
            "Acceptance requires PostgreSQL source and target databases."
        )
    if not parsed.host or not parsed.database:
        raise AcceptanceSafetyError(
            "Database URL must include an explicit host and database name."
        )
    host = parsed.host.casefold().rstrip(".")
    if host in {"localhost", "::1", "0:0:0:0:0:0:0:1"}:
        host = "127.0.0.1"
    return DatabaseIdentity(
        host=host,
        port=parsed.port or 5432,
        database=parsed.database,
    )


def redact_database_url(database_url: str) -> str:
    """Render a URL for diagnostics without exposing its password."""

    try:
        return make_url(database_url).render_as_string(hide_password=True)
    except (ArgumentError, TypeError, ValueError):
        return "<invalid-database-url>"


def _database_urls_from_environment(
    *,
    source_name: str,
    target_name: str,
    environment: Mapping[str, str],
) -> tuple[str, str]:
    """Resolve credential-bearing URLs by non-secret variable name only."""

    for label, name in (("source", source_name), ("target", target_name)):
        if (
            not name
            or not name[0].isalpha()
            or name != name.upper()
            or not all(character.isalnum() or character == "_" for character in name)
        ):
            raise AcceptanceSafetyError(
                f"The {label} database environment variable name is invalid."
            )
    if source_name == target_name:
        raise AcceptanceSafetyError(
            "Source and target database URLs must use different environment variable names."
        )
    missing = [name for name in (source_name, target_name) if not environment.get(name)]
    if missing:
        raise AcceptanceSafetyError(
            "Required database URL environment variable is absent: "
            + ", ".join(missing)
        )
    return environment[source_name], environment[target_name]


def validate_database_boundary(source_url: str, target_url: str) -> DatabaseBoundary:
    """Prove source/target separation before any subprocess or DB connection."""

    source_identity = canonical_database_identity(source_url)
    target_identity = canonical_database_identity(target_url)
    if source_identity == target_identity:
        raise AcceptanceSafetyError(
            "Source and target database identities are equal; acceptance writes are refused."
        )
    if target_identity.database == CANONICAL_TEST_DATABASE_NAME:
        raise AcceptanceSafetyError(
            "The canonical disposable test database cannot be an acceptance target."
        )
    if not _is_unique_acceptance_database_name(target_identity.database):
        raise AcceptanceSafetyError(
            "Target database name must use a unique lina_acceptance_<run> marker."
        )
    return DatabaseBoundary(
        source_identity=source_identity,
        target_identity=target_identity,
        source_url=make_url(source_url),
        target_url=make_url(target_url),
    )


def _is_unique_acceptance_database_name(database: str) -> bool:
    prefix = "lina_acceptance_"
    suffix = database.removeprefix(prefix)
    return (
        database.startswith(prefix)
        and len(suffix) >= 10
        and len(database.encode("utf-8")) <= 63
        and all(
            character.islower() or character.isdigit() or character == "_"
            for character in suffix
        )
        and any(character.isdigit() for character in suffix)
    )


def build_clone_commands(
    boundary: DatabaseBoundary, *, dump_path: Path
) -> list[CommandSpec]:
    """Build a source-read-only dump and target-only create/restore plan."""

    source = boundary.source_url
    target = boundary.target_url
    return [
        CommandSpec(
            purpose="source_dump",
            argv=(
                "pg_dump",
                "--host",
                str(source.host),
                "--port",
                str(source.port or 5432),
                "--username",
                str(source.username or ""),
                "--no-password",
                "--dbname",
                str(source.database),
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                "--file",
                str(dump_path),
            ),
            environment=_libpq_secret_environment(source),
        ),
        CommandSpec(
            purpose="target_create",
            argv=(
                "createdb",
                "--host",
                str(target.host),
                "--port",
                str(target.port or 5432),
                "--username",
                str(target.username or ""),
                "--no-password",
                "--maintenance-db",
                "postgres",
                str(target.database),
            ),
            environment=_libpq_secret_environment(target),
        ),
        CommandSpec(
            purpose="target_restore",
            argv=(
                "pg_restore",
                "--host",
                str(target.host),
                "--port",
                str(target.port or 5432),
                "--username",
                str(target.username or ""),
                "--no-password",
                "--dbname",
                str(target.database),
                "--no-owner",
                "--no-privileges",
                str(dump_path),
            ),
            environment=_libpq_secret_environment(target),
        ),
    ]


def _libpq_secret_environment(url: URL) -> dict[str, str]:
    environment: dict[str, str] = {}
    if url.password is not None:
        environment["PGPASSWORD"] = url.password
    sslmode = url.query.get("sslmode")
    if isinstance(sslmode, str):
        environment["PGSSLMODE"] = sslmode
    return environment


def execute_command(command: CommandSpec) -> None:
    """Execute a safe command without echoing arguments, environment, or stderr."""

    environment = {
        name: os.environ[name]
        for name in _SAFE_CHILD_ENVIRONMENT_KEYS
        if os.environ.get(name)
    }
    environment.setdefault("PATH", os.defpath)
    environment.update(command.environment)
    try:
        subprocess.run(
            command.argv,
            cwd=command.working_directory,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        return_code = getattr(error, "returncode", "unavailable")
        raise AcceptanceSafetyError(
            f"Acceptance command {command.purpose!r} failed with exit code {return_code}; details suppressed."
        ) from None


def validate_historical_counts(counts: HistoricalCounts, *, location: str) -> None:
    if counts != EXPECTED_HISTORICAL_COUNTS:
        raise AcceptanceSafetyError(
            f"{location} historical counts differ from expected 145/73/72/38; acceptance stopped."
        )


def historical_message_manifest(messages: Sequence[SourceMessage]) -> str:
    """Digest ordered raw authority fields without exposing their values."""

    _validate_source_message_order(messages)
    records = [
        {
            "id": str(message.id),
            "role": message.role,
            "content": message.content,
            "metadata": message.metadata,
            "ai_execution_id": (
                str(message.ai_execution_id) if message.ai_execution_id else None
            ),
            "created_at": message.created_at.isoformat(),
        }
        for message in messages
    ]
    encoded = json.dumps(
        records,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_historical_snapshots(
    expected: HistoricalSnapshot,
    observed: HistoricalSnapshot,
    *,
    location: str,
) -> None:
    """Require both aggregate and exact ordered raw-record preservation."""

    validate_historical_counts(observed.counts, location=location)
    if observed.raw_message_manifest_sha256 != expected.raw_message_manifest_sha256:
        raise AcceptanceSafetyError(
            f"{location} raw Message manifest differs from source-before; acceptance stopped."
        )


def build_reconstruction_payload(
    *, messages: Sequence[SourceMessage], session_id: UUID
) -> dict[str, object]:
    """Build one complete semantic boundary request for the Model Gateway."""

    _validate_source_message_order(messages)
    source_messages = [
        {
            "id": str(message.id),
            "role": message.role,
            "content": message.content,
            "created_at": message.created_at.isoformat(),
        }
        for message in messages
    ]
    model_input = {
        "acceptance_reconstruction": True,
        "session_id": str(session_id),
        "source_messages": source_messages,
    }
    instructions = (
        "Reconstruct contiguous semantic conversation Segments from the complete chronological raw message list. "
        "Use educational meaning and conversational continuity. Assign every message exactly once, preserve the "
        "supplied order, begin at Segment 1, and increase by exactly one only when meaningfully beginning a new "
        "conversation Segment on a Student message. Never begin a Segment on a Tutor message. Give a concise "
        "reason for the first message and every Segment transition; use null "
        "for all other boundary_reason values. These are acceptance reconstructions, not original live decisions."
    )
    return {
        "operation": ACCEPTANCE_RECONSTRUCTION_OPERATION,
        "instructions": instructions,
        "input": json.dumps(model_input, sort_keys=True, separators=(",", ":")),
        "response_schema": RECONSTRUCTION_RESPONSE_SCHEMA,
        "max_output_tokens": 32000,
        "source_messages": source_messages,
    }


def validate_reconstruction_output(
    output: Mapping[str, object], *, messages: Sequence[SourceMessage]
) -> ReconstructionEnvelope:
    """Require exact ordered coverage and contiguous Segment numbering."""

    _validate_source_message_order(messages)
    try:
        envelope = ReconstructionEnvelope.model_validate(output)
    except ValidationError:
        raise ReconstructionValidationError(
            "Reconstruction output does not satisfy the strict contract."
        ) from None
    expected = [message.id for message in messages]
    actual = [assignment.message_id for assignment in envelope.assignments]
    if actual != expected or len(set(actual)) != len(actual):
        raise ReconstructionValidationError(
            "Reconstruction must assign every source Message exactly once in chronological order."
        )
    sequences = [assignment.segment_sequence for assignment in envelope.assignments]
    if not sequences or sequences[0] != 1:
        raise ReconstructionValidationError(
            "Reconstruction must begin with Segment sequence 1."
        )
    previous = 0
    segment_has_student: dict[int, bool] = {}
    for message, assignment in zip(messages, envelope.assignments, strict=True):
        changed = assignment.segment_sequence != previous
        if assignment.segment_sequence not in {previous, previous + 1}:
            raise ReconstructionValidationError(
                "Segment sequences must be contiguous and nondecreasing."
            )
        if changed and assignment.boundary_reason is None:
            raise ReconstructionValidationError(
                "Every Segment boundary requires an auditable semantic reason."
            )
        if not changed and assignment.boundary_reason is not None:
            raise ReconstructionValidationError(
                "Only Segment boundaries may carry a boundary reason."
            )
        is_student = message.role.casefold() == "student"
        if changed and not is_student:
            raise ReconstructionValidationError(
                "The first message and every Segment transition must be a Student message."
            )
        segment_has_student[assignment.segment_sequence] = (
            segment_has_student.get(assignment.segment_sequence, False) or is_student
        )
        previous = assignment.segment_sequence
    if not all(segment_has_student.values()):
        raise ReconstructionValidationError(
            "Every reconstructed Segment must contain a raw Student message."
        )
    return envelope


def _validate_source_message_order(messages: Sequence[SourceMessage]) -> None:
    identities = [message.id for message in messages]
    chronological = sorted(
        messages, key=lambda message: (message.created_at, message.id)
    )
    if (
        not messages
        or len(set(identities)) != len(identities)
        or list(messages) != chronological
    ):
        raise ReconstructionValidationError(
            "Source Messages must be unique and chronologically ordered."
        )


def provider_disabled_plan(
    configuration: AcceptanceConfiguration,
    *,
    gateway_factory: Callable[[Session], object] | None = None,
) -> dict[str, object]:
    """Return a safe no-write/no-provider plan; do not construct the factory."""

    del gateway_factory
    boundary = validate_database_boundary(
        configuration.source_database_url,
        configuration.target_database_url,
    )
    return {
        "mode": "NO_WRITE_PREFLIGHT",
        "provider_execution": "DISABLED",
        "source_database": boundary.source_identity.safe_label,
        "target_database": boundary.target_identity.safe_label,
        "historical_session_id": str(HISTORICAL_SESSION_ID),
        "artifact_directory": str(configuration.artifact_directory),
    }


def _historical_snapshot(database_url: str) -> HistoricalSnapshot:
    engine = create_engine(normalize_database_url(database_url), pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                message_rows = (
                    connection.execute(
                        text(
                            "SELECT id, role, content, metadata, ai_execution_id, created_at "
                            "FROM learning_messages WHERE session_id = :session_id "
                            "ORDER BY created_at, id"
                        ),
                        {"session_id": HISTORICAL_SESSION_ID},
                    )
                    .mappings()
                    .all()
                )
                candidates = connection.execute(
                    text(
                        "SELECT COUNT(*) FROM candidate_events WHERE session_id = :session_id"
                    ),
                    {"session_id": HISTORICAL_SESSION_ID},
                ).scalar_one()
                transaction.rollback()
            except Exception:
                transaction.rollback()
                raise
        messages = [
            SourceMessage(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                created_at=row["created_at"],
                metadata=row["metadata"],
                ai_execution_id=row["ai_execution_id"],
            )
            for row in message_rows
        ]
        counts = HistoricalCounts(
            messages=len(messages),
            student_messages=sum(
                message.role.casefold() == "student" for message in messages
            ),
            tutor_messages=sum(
                message.role.casefold() == "tutor" for message in messages
            ),
            candidates=int(candidates),
        )
        return HistoricalSnapshot(
            counts=counts,
            raw_message_manifest_sha256=historical_message_manifest(messages),
        )
    except (
        AttributeError,
        KeyError,
        ReconstructionValidationError,
        SQLAlchemyError,
        TypeError,
        ValueError,
    ):
        raise AcceptanceSafetyError(
            "Historical raw-record snapshot failed; database details suppressed."
        ) from None
    finally:
        engine.dispose()


def _migrate_target(target_database_url: str) -> None:
    with tempfile.TemporaryDirectory(prefix="lina-acceptance-migrate-") as temporary:
        command = CommandSpec(
            purpose="target_migrate",
            argv=(
                sys.executable,
                "-m",
                "alembic",
                "-c",
                str(ROOT / "alembic.ini"),
                "upgrade",
                "head",
            ),
            environment={
                "DATABASE_URL": target_database_url,
                "PYTHONPATH": str(ROOT),
            },
            # Settings.env_file is relative to cwd. An empty temporary cwd makes
            # explicit process environment the only configuration source.
            working_directory=Path(temporary),
        )
        execute_command(command)


def _target_alembic_revision(target_database_url: str) -> str:
    engine = create_engine(
        normalize_database_url(target_database_url), pool_pre_ping=True
    )
    try:
        with engine.connect() as connection:
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        if not isinstance(revision, str) or not revision:
            raise AcceptanceSafetyError("Target Alembic revision is unavailable.")
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        heads = set(
            ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini"))).get_heads()
        )
        if heads != {revision}:
            raise AcceptanceSafetyError(
                "Target database is not at the single current Alembic head."
            )
        return revision
    except AcceptanceSafetyError:
        raise
    except (CommandError, OSError, SQLAlchemyError, TypeError, ValueError):
        raise AcceptanceSafetyError(
            "Target schema inspection failed; database details suppressed."
        ) from None
    finally:
        engine.dispose()


def prepare_isolated_target(
    configuration: AcceptanceConfiguration,
    *,
    command_runner: Callable[[CommandSpec], None] = execute_command,
) -> dict[str, object]:
    """Clone source read-only, migrate target, and prove count preservation."""

    boundary = validate_database_boundary(
        configuration.source_database_url,
        configuration.target_database_url,
    )
    source_before = _historical_snapshot(configuration.source_database_url)
    validate_historical_counts(source_before.counts, location="source-before")
    with tempfile.TemporaryDirectory(prefix="lina-acceptance-dump-") as temporary:
        dump_path = Path(temporary) / "source.dump"
        for command in build_clone_commands(boundary, dump_path=dump_path):
            command_runner(command)
    _migrate_target(configuration.target_database_url)
    target_after = _historical_snapshot(configuration.target_database_url)
    validate_historical_snapshots(
        source_before,
        target_after,
        location="target-after-migration",
    )
    source_after = _historical_snapshot(configuration.source_database_url)
    validate_historical_snapshots(
        source_before,
        source_after,
        location="source-after",
    )
    return {
        "source_database": boundary.source_identity.safe_label,
        "target_database": boundary.target_identity.safe_label,
        "source_before": _snapshot_report(source_before),
        "target_after_migration": _snapshot_report(target_after),
        "source_after": _snapshot_report(source_after),
        "target_alembic_revision": _target_alembic_revision(
            configuration.target_database_url
        ),
        "source_write_operations": 0,
    }


def _snapshot_report(snapshot: HistoricalSnapshot) -> dict[str, object]:
    return {
        "messages": snapshot.counts.messages,
        "student_messages": snapshot.counts.student_messages,
        "tutor_messages": snapshot.counts.tutor_messages,
        "candidates": snapshot.counts.candidates,
        "raw_message_manifest_sha256": snapshot.raw_message_manifest_sha256,
    }


def _read_resume_target_state(
    target_database_url: str,
    artifact_directory: Path,
) -> ResumeTargetState:
    """Inspect only the isolated target state required for safe reconstruction resume."""

    engine = create_engine(
        normalize_database_url(target_database_url),
        pool_pre_ping=True,
    )
    try:
        with Session(engine) as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            learning_session = session.get(LearningSession, HISTORICAL_SESSION_ID)
            if learning_session is None:
                raise AcceptanceSafetyError(
                    "Historical Session is absent from the resume target."
                )
            segment_count = session.scalar(
                select(func.count())
                .select_from(LearningSegment)
                .where(LearningSegment.session_id == learning_session.id)
            )
            assigned_message_count = session.scalar(
                select(func.count())
                .select_from(LearningMessage)
                .where(
                    LearningMessage.session_id == learning_session.id,
                    LearningMessage.segment_id.is_not(None),
                )
            )
            operation_id = _required_reconstruction_operation_id(learning_session.id)
            stage = _audit_stage_paths(artifact_directory, operation_id)
            return ResumeTargetState(
                intelligence_pipeline=learning_session.intelligence_pipeline,
                segment_count=int(segment_count or 0),
                assigned_message_count=int(assigned_message_count or 0),
                pending_audit_exists=stage.pending_json_path.exists(),
                committed_audit_exists=(
                    stage.final_json_path.exists() or stage.final_markdown_path.exists()
                ),
            )
    except AcceptanceSafetyError:
        raise
    except (OSError, SQLAlchemyError, TypeError, ValueError):
        raise AcceptanceSafetyError(
            "Resume target state inspection failed; details suppressed."
        ) from None
    finally:
        engine.dispose()


def _validate_resume_target_state(state: ResumeTargetState) -> None:
    if state.intelligence_pipeline != "legacy-session-evidence-v1":
        raise AcceptanceSafetyError(
            "Existing-target reconstruction resume refused: historical pipeline is not the clean migrated state."
        )
    if state.segment_count or state.assigned_message_count:
        raise AcceptanceSafetyError(
            "Existing-target reconstruction resume refused: Segment state already exists."
        )
    if state.pending_audit_exists or state.committed_audit_exists:
        raise AcceptanceSafetyError(
            "Existing-target reconstruction resume refused: reconstruction audit state already exists."
        )


def resume_real_reconstruction(
    configuration: AcceptanceConfiguration,
    *,
    environment: Mapping[str, str] = os.environ,
) -> dict[str, object]:
    """Resume only reconstruction on a previously cloned, untouched target."""

    if not configuration.execute_reconstruction:
        raise AcceptanceSafetyError(
            "Existing-target reconstruction resume requires explicit resume mode."
        )
    boundary = validate_database_boundary(
        configuration.source_database_url,
        configuration.target_database_url,
    )
    source_snapshot = _historical_snapshot(configuration.source_database_url)
    validate_historical_counts(source_snapshot.counts, location="resume-source")
    target_snapshot = _historical_snapshot(configuration.target_database_url)
    validate_historical_snapshots(
        source_snapshot,
        target_snapshot,
        location="resume-target",
    )
    target_revision = _target_alembic_revision(configuration.target_database_url)
    state = _read_resume_target_state(
        configuration.target_database_url,
        configuration.artifact_directory,
    )
    _validate_resume_target_state(state)
    reconstruction = execute_real_reconstruction(
        configuration,
        environment=environment,
    )
    return {
        "mode": "RESUME_EXISTING_TARGET_RECONSTRUCTION",
        "source_database": boundary.source_identity.safe_label,
        "target_database": boundary.target_identity.safe_label,
        "source_snapshot": _snapshot_report(source_snapshot),
        "target_snapshot": _snapshot_report(target_snapshot),
        "target_alembic_revision": target_revision,
        "source_write_operations": 0,
        "reconstruction": reconstruction,
    }


def _ordered_messages(
    session: Session,
) -> tuple[LearningSession, list[LearningMessage], list[SourceMessage]]:
    learning_session = session.get(LearningSession, HISTORICAL_SESSION_ID)
    if learning_session is None:
        raise AcceptanceSafetyError(
            "Historical Session is absent from the isolated target."
        )
    rows = list(
        session.scalars(
            select(LearningMessage)
            .where(LearningMessage.session_id == learning_session.id)
            .order_by(LearningMessage.created_at, LearningMessage.id)
        )
    )
    source = [
        SourceMessage(
            id=row.id,
            role=row.role,
            content=row.content,
            created_at=row.created_at,
            metadata=row.payload,
            ai_execution_id=row.ai_execution_id,
        )
        for row in rows
    ]
    if len(source) != EXPECTED_HISTORICAL_COUNTS.messages:
        raise AcceptanceSafetyError(
            "Isolated target no longer contains the complete historical message list."
        )
    return learning_session, rows, source


def _raw_message_fingerprint(messages: Sequence[LearningMessage]) -> str:
    source_messages = [
        SourceMessage(
            id=message.id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            metadata=message.payload,
            ai_execution_id=message.ai_execution_id,
        )
        for message in messages
    ]
    return historical_message_manifest(source_messages)


def _provider_settings(
    target_database_url: str, environment: Mapping[str, str]
) -> Settings:
    required = ("MODEL_PROVIDER", "MODEL_NAME", "MODEL_API_KEY")
    missing = [name for name in required if not environment.get(name)]
    if missing:
        raise AcceptanceSafetyError(
            "Real reconstruction environment is incomplete; required variable names: "
            + ", ".join(missing)
        )
    if (
        environment.get("MODEL_PROVIDER") != "openai"
        or environment.get("MODEL_NAME") != "gpt-5.6-luna"
    ):
        raise AcceptanceSafetyError(
            "Real reconstruction requires the configured openai / gpt-5.6-luna route."
        )
    return Settings(
        _env_file=None,
        # BaseSettings still reads process variables when dotenv loading is
        # disabled. A per-call unguessable prefix isolates this instance so
        # only the explicit, already-validated kwargs below are consumed.
        _env_prefix=f"__LINA_ACCEPTANCE_EXPLICIT_{uuid4().hex.upper()}__",
        database_url=target_database_url,
        model_provider="openai",
        model_name="gpt-5.6-luna",
        model_api_key=environment["MODEL_API_KEY"],
        model_base_url=environment.get("MODEL_BASE_URL"),
    )


def _acceptance_model_timeout_seconds(environment: Mapping[str, str]) -> float:
    raw = environment.get(ACCEPTANCE_MODEL_TIMEOUT_ENV_VAR)
    if raw is None:
        return DEFAULT_ACCEPTANCE_MODEL_TIMEOUT_SECONDS
    try:
        timeout = int(raw)
    except (TypeError, ValueError):
        timeout = 0
    if (
        not MIN_ACCEPTANCE_MODEL_TIMEOUT_SECONDS
        <= timeout
        <= MAX_ACCEPTANCE_MODEL_TIMEOUT_SECONDS
    ):
        raise AcceptanceSafetyError(
            f"{ACCEPTANCE_MODEL_TIMEOUT_ENV_VAR} must be an integer between 30 and 300 seconds."
        )
    return float(timeout)


def _create_acceptance_reconstruction_gateway(
    session: object,
    *,
    settings: Settings,
    environment: Mapping[str, str],
    gateway_factory: Callable[..., object] = create_segment_evidence_gateway,
    provider_factory: Callable[..., object] = OpenAIResponsesProvider,
) -> tuple[object, float]:
    """Inject an acceptance-only provider timeout through the Model Gateway factory."""

    if settings.model_api_key is None:
        raise AcceptanceSafetyError(
            "Real reconstruction requires the explicit model API key."
        )
    timeout_seconds = _acceptance_model_timeout_seconds(environment)
    provider = provider_factory(
        api_key=settings.model_api_key.get_secret_value(),
        base_url=settings.model_base_url,
        timeout_seconds=timeout_seconds,
    )
    gateway = gateway_factory(
        session,
        settings=settings,
        openai_provider=provider,
    )
    return gateway, timeout_seconds


def _required_reconstruction_operation_id(session_id: UUID) -> UUID:
    return uuid5(
        NAMESPACE_URL,
        f"{ACCEPTANCE_RECONSTRUCTION_OPERATION}:{session_id}:{ACCEPTANCE_RECONSTRUCTION_VERSION}",
    )


def _verified_reconstruction_execution(
    execution: AIExecution | None,
    *,
    learning_session: LearningSession,
    operation_id: UUID,
) -> AIExecution:
    if (
        execution is None
        or execution.success is not True
        or execution.task != ModelTask.SEGMENT_EVIDENCE.value
        or execution.provider != "openai"
        or execution.model != "gpt-5.6-luna"
        or execution.operation_type != ACCEPTANCE_RECONSTRUCTION_OPERATION
        or execution.operation_id != operation_id
        or execution.learning_session_id != learning_session.id
        or execution.student_id != learning_session.student_id
    ):
        raise AcceptanceSafetyError(
            "Real reconstruction ledger lineage does not match the required acceptance route."
        )
    return execution


def _preflight_artifact_directory(directory: Path) -> None:
    """Prove the audit destination is writable before any provider operation."""

    try:
        directory.mkdir(parents=True, exist_ok=True)
        if not directory.is_dir():
            raise OSError("not a directory")
        descriptor, probe_name = tempfile.mkstemp(
            prefix=".lina-acceptance-write-probe-",
            dir=directory,
        )
        os.close(descriptor)
        Path(probe_name).unlink()
    except OSError:
        raise AcceptanceSafetyError(
            "Acceptance audit destination is not safely writable."
        ) from None


def _atomic_write_text(path: Path, content: str) -> None:
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except (SQLAlchemyError, TypeError, ValueError):
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def _stage_audit_artifact(
    directory: Path,
    audit: Mapping[str, object],
) -> AuditStage:
    """Persist a pending audit inside the DB transaction; it claims no commit."""

    operation_id = UUID(str(audit["operation_id"]))
    stage = _audit_stage_paths(directory, operation_id)
    pending = dict(audit)
    pending["publication_state"] = "PENDING_DATABASE_COMMIT"
    _atomic_write_text(
        stage.pending_json_path,
        json.dumps(pending, indent=2, sort_keys=True) + "\n",
    )
    return stage


def _audit_stage_paths(directory: Path, operation_id: UUID) -> AuditStage:
    stem = f"historical-segment-reconstruction.{operation_id}"
    return AuditStage(
        pending_json_path=directory / f".{stem}.pending.json",
        final_json_path=directory / f"{stem}.json",
        final_markdown_path=directory / f"{stem}.md",
    )


def _audit_markdown(audit: Mapping[str, object]) -> str:
    assignments = audit.get("assignments")
    count = len(assignments) if isinstance(assignments, list) else 0
    return (
        "# Historical Segment Reconstruction\n\n"
        f"- Session: `{audit['historical_session_id']}`\n"
        f"- Provider/model: `{audit['provider']} / {audit['model']}`\n"
        f"- Model Gateway execution: `{audit['ai_execution_id']}`\n"
        f"- Messages assigned: `{count}`\n"
        "- Database commit: `COMMITTED`\n"
        "- Classification: acceptance reconstruction; not an original live Segment decision.\n"
        "- Raw Message authority fields preserved: `true`\n"
    )


def _publish_staged_audit(stage: AuditStage) -> dict[str, object]:
    """Publish final artifacts only after the caller's DB commit succeeds."""

    pending = json.loads(stage.pending_json_path.read_text(encoding="utf-8"))
    if (
        not isinstance(pending, dict)
        or pending.get("publication_state") != "PENDING_DATABASE_COMMIT"
    ):
        raise AcceptanceSafetyError("Pending reconstruction audit is invalid.")
    committed = dict(pending)
    committed["publication_state"] = "COMMITTED"
    _atomic_write_text(
        stage.final_json_path,
        json.dumps(committed, indent=2, sort_keys=True) + "\n",
    )
    _atomic_write_text(stage.final_markdown_path, _audit_markdown(committed))
    stage.pending_json_path.unlink()
    return committed


def _commit_with_staged_audit(
    session: object,
    *,
    operation: Callable[[], dict[str, object]],
    stager: Callable[[dict[str, object]], AuditStage],
) -> tuple[dict[str, object], AuditStage]:
    """Make staging failure part of the same failure boundary as DB mutation."""

    with session.begin():
        audit = operation()
        stage = stager(audit)
    return audit, stage


def recover_staged_reconstruction_audit(
    configuration: AcceptanceConfiguration,
    *,
    operation_id: UUID,
) -> dict[str, object]:
    """Publish a pending audit only after verifying its committed DB ledger."""

    validate_database_boundary(
        configuration.source_database_url,
        configuration.target_database_url,
    )
    _preflight_artifact_directory(configuration.artifact_directory)
    stage = _audit_stage_paths(configuration.artifact_directory, operation_id)
    pending_exists = stage.pending_json_path.is_file()
    selected_path = stage.pending_json_path if pending_exists else stage.final_json_path
    if not selected_path.is_file():
        raise AcceptanceSafetyError(
            "No pending or committed reconstruction audit exists for that operation."
        )
    try:
        selected_audit = json.loads(selected_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise AcceptanceSafetyError(
            "Reconstruction audit is unreadable or invalid."
        ) from None
    if not isinstance(selected_audit, dict):
        raise AcceptanceSafetyError("Reconstruction audit is invalid.")
    try:
        selected_execution_id = UUID(str(selected_audit["ai_execution_id"]))
    except (KeyError, TypeError, ValueError):
        raise AcceptanceSafetyError(
            "Reconstruction audit ledger identity is invalid."
        ) from None
    engine = create_engine(
        normalize_database_url(configuration.target_database_url),
        pool_pre_ping=True,
    )
    try:
        with Session(engine) as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            execution = session.get(AIExecution, selected_execution_id)
            learning_session = session.get(LearningSession, HISTORICAL_SESSION_ID)
            if learning_session is None:
                raise AcceptanceSafetyError(
                    "Committed reconstruction Session is unavailable."
                )
            verified = _verified_reconstruction_execution(
                execution,
                learning_session=learning_session,
                operation_id=operation_id,
            )
            if str(verified.id) != selected_audit.get("ai_execution_id"):
                raise AcceptanceSafetyError(
                    "Audit does not match persisted ledger lineage."
                )
    except AcceptanceSafetyError:
        raise
    except (SQLAlchemyError, TypeError, ValueError):
        raise AcceptanceSafetyError(
            "Pending audit recovery could not verify target ledger lineage."
        ) from None
    finally:
        engine.dispose()
    if not pending_exists:
        if selected_audit.get("publication_state") != "COMMITTED":
            raise AcceptanceSafetyError(
                "Existing reconstruction audit is not committed."
            )
        return selected_audit
    try:
        return _publish_staged_audit(stage)
    except (
        AcceptanceSafetyError,
        KeyError,
        OSError,
        TypeError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
    ):
        raise AcceptanceSafetyError(
            "Audit recovery publication failed; the pending audit was retained."
        ) from None


def execute_real_reconstruction(
    configuration: AcceptanceConfiguration,
    *,
    environment: Mapping[str, str] = os.environ,
    gateway_factory: Callable[..., ModelGateway] = create_segment_evidence_gateway,
) -> dict[str, object]:
    """Call real Luna through the Gateway and persist Segments on target only."""

    validate_database_boundary(
        configuration.source_database_url, configuration.target_database_url
    )
    if not configuration.execute_reconstruction:
        raise AcceptanceSafetyError(
            "Real reconstruction requires explicit --execute-reconstruction."
        )
    _preflight_artifact_directory(configuration.artifact_directory)
    settings = _provider_settings(configuration.target_database_url, environment)
    engine = create_engine(
        normalize_database_url(configuration.target_database_url), pool_pre_ping=True
    )
    try:
        with Session(engine) as session:

            def reconstruct() -> dict[str, object]:
                learning_session, rows, source_messages = _ordered_messages(session)
                if session.scalar(
                    select(func.count())
                    .select_from(LearningSegment)
                    .where(LearningSegment.session_id == learning_session.id)
                ):
                    raise AcceptanceSafetyError(
                        "Target Session already has Segments; reconstruction refused."
                    )
                if any(message.segment_id is not None for message in rows):
                    raise AcceptanceSafetyError(
                        "Target Messages already have Segment assignments; reconstruction refused."
                    )
                before_fingerprint = _raw_message_fingerprint(rows)
                gateway, timeout_seconds = _create_acceptance_reconstruction_gateway(
                    session,
                    settings=settings,
                    environment=environment,
                    gateway_factory=gateway_factory,
                )
                route = gateway.route_for(ModelTask.SEGMENT_EVIDENCE)
                if route.provider != "openai" or route.model != "gpt-5.6-luna":
                    raise AcceptanceSafetyError(
                        "Gateway route is not the required openai / gpt-5.6-luna route."
                    )
                operation_id = _required_reconstruction_operation_id(
                    learning_session.id
                )
                result = gateway.execute(
                    ModelTask.SEGMENT_EVIDENCE,
                    build_reconstruction_payload(
                        messages=source_messages, session_id=learning_session.id
                    ),
                    lineage=AIExecutionLineage(
                        operation=ACCEPTANCE_RECONSTRUCTION_OPERATION,
                        operation_id=operation_id,
                        student_id=learning_session.student_id,
                        learning_session_id=learning_session.id,
                    ),
                )
                envelope = validate_reconstruction_output(
                    result.output, messages=source_messages
                )
                segment_ids = _persist_reconstructed_segments(
                    session,
                    learning_session=learning_session,
                    messages=rows,
                    envelope=envelope,
                )
                if _raw_message_fingerprint(rows) != before_fingerprint:
                    raise AcceptanceSafetyError(
                        "Raw Message authority changed during reconstruction."
                    )
                execution = _verified_reconstruction_execution(
                    session.get(AIExecution, result.execution_id),
                    learning_session=learning_session,
                    operation_id=operation_id,
                )
                return {
                    "version": ACCEPTANCE_RECONSTRUCTION_VERSION,
                    "historical_session_id": str(learning_session.id),
                    "acceptance_reconstruction": True,
                    "original_live_segment_decision": False,
                    "task": execution.task,
                    "operation": execution.operation_type,
                    "provider": execution.provider,
                    "model": execution.model,
                    "execution_success": execution.success,
                    "acceptance_model_timeout_seconds": timeout_seconds,
                    "ai_execution_id": str(execution.id),
                    "operation_id": str(execution.operation_id),
                    "raw_message_fingerprint": before_fingerprint,
                    "raw_message_fields_preserved": True,
                    "segment_ids": {
                        str(sequence): str(identifier)
                        for sequence, identifier in segment_ids.items()
                    },
                    "assignments": [
                        assignment.model_dump(mode="json")
                        for assignment in envelope.assignments
                    ],
                }

            audit, stage = _commit_with_staged_audit(
                session,
                operation=reconstruct,
                stager=lambda audit: _stage_audit_artifact(
                    configuration.artifact_directory,
                    audit,
                ),
            )
        try:
            return _publish_staged_audit(stage)
        except (
            AcceptanceSafetyError,
            KeyError,
            OSError,
            TypeError,
            UnicodeError,
            ValueError,
            json.JSONDecodeError,
        ):
            raise AcceptanceSafetyError(
                "Database reconstruction committed but audit publication is pending; rerun with "
                f"--recover-audit-operation-id {audit['operation_id']}."
            ) from None
    except AcceptanceSafetyError:
        raise
    except Exception:  # noqa: BLE001 -- redact all provider/DB failures at the operator boundary.
        raise AcceptanceSafetyError(
            "Real reconstruction failed; provider/database details suppressed."
        ) from None
    finally:
        engine.dispose()


def _persist_reconstructed_segments(
    session: Session,
    *,
    learning_session: LearningSession,
    messages: Sequence[LearningMessage],
    envelope: ReconstructionEnvelope,
) -> dict[int, UUID]:
    grouped: dict[int, list[tuple[LearningMessage, ReconstructionAssignment]]] = {}
    for message, assignment in zip(messages, envelope.assignments, strict=True):
        grouped.setdefault(assignment.segment_sequence, []).append(
            (message, assignment)
        )
    segment_ids: dict[int, UUID] = {}
    final_sequence = max(grouped)
    for sequence, items in grouped.items():
        first_message, boundary = items[0]
        last_message = items[-1][0]
        segment = LearningSegment(
            session_id=learning_session.id,
            sequence=sequence,
            structured_state={
                "acceptance_reconstruction": True,
                "reconstruction_version": ACCEPTANCE_RECONSTRUCTION_VERSION,
                "boundary_reason": boundary.boundary_reason,
            },
            created_at=first_message.created_at,
            closed_at=last_message.created_at,
            closure_reason=(
                "SESSION_CLOSED"
                if sequence == final_sequence
                else "NEXT_SEGMENT_CREATED"
            ),
        )
        session.add(segment)
        session.flush()
        segment_ids[sequence] = segment.id
        for message, _ in items:
            message.segment_id = segment.id
    learning_session.intelligence_pipeline = ACCEPTANCE_PIPELINE
    session.flush()
    return segment_ids


def _historical_acceptance_operation_id() -> UUID:
    """Return the stable identity for the fixed historical acceptance journey."""

    return uuid5(
        NAMESPACE_URL,
        f"{HISTORICAL_ACCEPTANCE_OPERATION}:{HISTORICAL_SESSION_ID}",
    )


def _validate_historical_active_job_scope(
    jobs: Sequence[object], *, session_id: UUID
) -> None:
    """Refuse a scoped worker if it could claim the same job type for another Session."""

    for job in jobs:
        status = getattr(job, "status", None)
        payload = getattr(job, "payload", None)
        if status not in {JobStatus.PENDING.value, JobStatus.RUNNING.value}:
            continue
        raw_session_id = payload.get("session_id") if isinstance(payload, dict) else None
        if raw_session_id != str(session_id):
            raise AcceptanceSafetyError(
                "Historical worker scope contains claimable jobs for other Sessions."
            )


def _validate_completed_review_sources(
    review: object,
    *,
    segment_message_roles: Mapping[UUID, str],
) -> int:
    """Verify persisted Finding source IDs are exact raw members of one Segment."""

    if getattr(review, "status", None) != "COMPLETED":
        raise AcceptanceSafetyError(
            "Historical Segment Review is not durably COMPLETED."
        )
    output = getattr(review, "output", None)
    findings = output.get("findings") if isinstance(output, dict) else None
    if (
        not isinstance(output, dict)
        or output.get("version") != SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
        or not isinstance(findings, list)
    ):
        raise AcceptanceSafetyError(
            "Historical Segment Review output is not the accepted strict schema."
        )
    for finding in findings:
        raw_ids = finding.get("source_message_ids") if isinstance(finding, dict) else None
        if not isinstance(raw_ids, list) or not raw_ids:
            raise AcceptanceSafetyError(
                "Historical Segment Review Finding has invalid source lineage."
            )
        try:
            source_ids = [UUID(str(value)) for value in raw_ids]
        except (TypeError, ValueError):
            raise AcceptanceSafetyError(
                "Historical Segment Review Finding has invalid source lineage."
            ) from None
        if (
            len(set(source_ids)) != len(source_ids)
            or any(source_id not in segment_message_roles for source_id in source_ids)
            or not any(
                segment_message_roles[source_id].casefold() == "student"
                for source_id in source_ids
            )
        ):
            raise AcceptanceSafetyError(
                "Historical Segment Review Finding has invalid source lineage."
            )
    return len(findings)


def _validate_segment_review_execution(
    review: object,
    *,
    execution: object,
    expected_student_id: UUID,
    expected_segment_id: UUID,
) -> object:
    """Require the exact production Model Gateway lineage for one Review."""

    review_id = getattr(review, "id", None)
    expected_operation_id = (
        uuid5(NAMESPACE_URL, f"segment-learning-review:{review_id}")
        if isinstance(review_id, UUID)
        else None
    )
    if (
        expected_operation_id is None
        or getattr(review, "student_id", None) != expected_student_id
        or getattr(review, "session_id", None) != HISTORICAL_SESSION_ID
        or getattr(review, "segment_id", None) != expected_segment_id
        or getattr(review, "ai_execution_id", None) != getattr(execution, "id", None)
        or getattr(execution, "success", None) is not True
        or getattr(execution, "task", None) != ModelTask.SEGMENT_EVIDENCE.value
        or getattr(execution, "provider", None) != "openai"
        or getattr(execution, "model", None) != "gpt-5.6-luna"
        or getattr(execution, "student_id", None) != expected_student_id
        or getattr(execution, "learning_session_id", None)
        != HISTORICAL_SESSION_ID
        or getattr(execution, "operation_type", None) != "segment_learning_review"
        or getattr(execution, "operation_id", None) != expected_operation_id
    ):
        raise AcceptanceSafetyError(
            "Historical Review execution ledger lineage does not match the exact production Segment Review."
        )
    return execution


def _derive_historical_atomicity(
    snapshot: Mapping[str, object],
) -> dict[str, object]:
    """Derive an activation verdict only from explicitly inspected durable rows."""

    authorities = snapshot.get("authorities")
    runs = snapshot.get("processing_runs")
    counts = snapshot.get("derived_counts")
    if (
        not isinstance(authorities, list)
        or not isinstance(runs, list)
        or not isinstance(counts, dict)
        or any(
            not isinstance(counts.get(name), int)
            for name in (
                "events",
                "evidence",
                "current_states",
                "patterns",
                "decision_views",
                "cards",
            )
        )
    ):
        return {
            "atomicity_verdict": "INSPECTION_INCOMPLETE",
            "partial_session_activation_detected": None,
            "selected_processing_run_id": None,
        }
    derived_total = sum(int(value) for value in counts.values())
    if not authorities and not runs and derived_total == 0:
        return {
            "atomicity_verdict": "NO_SESSION_ACTIVATION",
            "partial_session_activation_detected": False,
            "selected_processing_run_id": None,
        }
    if len(authorities) != 1:
        return {
            "atomicity_verdict": "INCONSISTENT_OR_PARTIAL_ACTIVATION",
            "partial_session_activation_detected": True,
            "selected_processing_run_id": None,
        }
    authority = authorities[0]
    selected_id = (
        authority.get("evidence_processing_run_id")
        if isinstance(authority, dict)
        else None
    )
    matching = [
        run
        for run in runs
        if isinstance(run, dict) and run.get("id") == selected_id
    ]
    if (
        not isinstance(authority, dict)
        or authority.get("reprocess_run_id") is not None
        or not isinstance(selected_id, str)
        or len(runs) != 1
        or len(matching) != 1
        or matching[0].get("status") != "COMPLETED"
        or matching[0].get("pipeline") != SESSION_FINALIZATION_PIPELINE
        or counts.get("events") != counts.get("evidence")
    ):
        return {
            "atomicity_verdict": "INCONSISTENT_OR_PARTIAL_ACTIVATION",
            "partial_session_activation_detected": True,
            "selected_processing_run_id": selected_id,
        }
    return {
        "atomicity_verdict": "COMPLETE_SESSION_ACTIVATION_PRESENT",
        "partial_session_activation_detected": False,
        "selected_processing_run_id": selected_id,
    }


def _historical_artifact_paths(directory: Path) -> tuple[Path, Path]:
    operation_id = _historical_acceptance_operation_id()
    stem = f"historical-intelligence-acceptance.{operation_id}"
    return directory / f"{stem}.json", directory / f"{stem}.md"


def _historical_acceptance_markdown(report: Mapping[str, object]) -> str:
    durable_state = report.get("durable_state")
    durable_state = durable_state if isinstance(durable_state, dict) else {}
    review_rows = report.get("segment_reviews")
    if not isinstance(review_rows, list):
        durable_reviews = durable_state.get("reviews")
        review_rows = durable_reviews if isinstance(durable_reviews, list) else []
    review_count = sum(
        isinstance(review, dict) and review.get("status") == "COMPLETED"
        for review in review_rows
    )
    review_statuses = durable_state.get("review_status_counts")
    if not isinstance(review_statuses, dict):
        review_statuses = {}
        for review in review_rows:
            status = review.get("status") if isinstance(review, dict) else None
            if isinstance(status, str):
                review_statuses[status] = int(review_statuses.get(status, 0)) + 1
    staged_findings = durable_state.get("staged_finding_count")
    if not isinstance(staged_findings, int):
        staged_findings = sum(
            int(review.get("finding_count", 0))
            for review in review_rows
            if isinstance(review, dict)
            and isinstance(review.get("finding_count", 0), int)
        )
    finalization = report.get("finalization")
    finalization = finalization if isinstance(finalization, dict) else {}
    derived_counts = durable_state.get("derived_counts")
    derived_counts = derived_counts if isinstance(derived_counts, dict) else {}
    event_count = finalization.get("event_count", derived_counts.get("events"))
    evidence_count = finalization.get(
        "evidence_count", derived_counts.get("evidence")
    )
    withheld_count = finalization.get(
        "withheld_finding_count",
        durable_state.get("withheld_finding_count"),
    )
    selected_run_id = finalization.get(
        "processing_run_id", durable_state.get("selected_processing_run_id")
    )
    activation_verdict = durable_state.get("atomicity_verdict")
    if activation_verdict is None and report.get("database_end_to_end_verified") is True:
        activation_verdict = "COMPLETE_SESSION_ACTIVATION_PRESENT"
    job_status_counts: dict[str, int] = {}
    jobs = durable_state.get("jobs")
    if isinstance(jobs, list):
        for job in jobs:
            if not isinstance(job, dict):
                continue
            job_type = job.get("job_type")
            status = job.get("status")
            if isinstance(job_type, str) and isinstance(status, str):
                key = f"{job_type}:{status}"
                job_status_counts[key] = job_status_counts.get(key, 0) + 1
    else:
        for key, job_type in (
            ("review_jobs", SEGMENT_LEARNING_REVIEW_JOB),
            ("finalization_job", SESSION_INTELLIGENCE_FINALIZE_JOB),
        ):
            job_rows = report.get(key)
            if not isinstance(job_rows, list):
                continue
            for job in job_rows:
                status = job.get("status") if isinstance(job, dict) else None
                if isinstance(status, str):
                    summary_key = f"{job_type}:{status}"
                    job_status_counts[summary_key] = (
                        job_status_counts.get(summary_key, 0) + 1
                    )
    job_summary = ", ".join(
        f"{key}={count}" for key, count in sorted(job_status_counts.items())
    ) or "not separately inventoried"
    real_luna_verified = report.get("real_luna_verified") is True
    execution_taxonomy = (
        str(report.get("execution_taxonomy", "CODEX_REPORTED_REAL_MODEL_VERIFICATION"))
        if real_luna_verified
        else "NOT VERIFIED"
    )
    authorities = durable_state.get("authorities")
    authority_count = (
        len(authorities)
        if isinstance(authorities, list)
        else (1 if finalization.get("authority_id") is not None else None)
    )
    current_state_count = finalization.get(
        "current_state_count", derived_counts.get("current_states")
    )
    pattern_count = finalization.get(
        "pattern_count", derived_counts.get("patterns")
    )
    decision_count = finalization.get(
        "decision_view_count", derived_counts.get("decision_views")
    )
    card_count = finalization.get("card_count", derived_counts.get("cards"))
    return (
        "# Historical Full-System Intelligence Acceptance\n\n"
        f"- Session: `{report.get('historical_session_id')}`\n"
        f"- Status: `{report.get('status')}`\n"
        f"- Durable Segment Reviews completed: `{review_count}`\n"
        f"- Review statuses: `{json.dumps(review_statuses, sort_keys=True)}`\n"
        f"- Staged / withheld Findings: `{staged_findings} / {withheld_count}`\n"
        f"- Job statuses: `{job_summary}`\n"
        f"- Session authorities: `{authority_count}`\n"
        f"- Processing run: `{selected_run_id}`\n"
        f"- Events / Evidence: `{event_count} / {evidence_count}`\n"
        f"- Current State / Pattern / Decision / Card: `"
        f"{current_state_count} / {pattern_count} / {decision_count} / {card_count}`\n"
        f"- Activation verdict: `{activation_verdict}`\n"
        f"- Real Luna verified: `{str(real_luna_verified).lower()}`\n"
        f"- Database end-to-end verified: `"
        f"{str(report.get('database_end_to_end_verified') is True).lower()}`\n"
        f"- Execution taxonomy: `{execution_taxonomy}`\n"
        "- Raw Student/Tutor content: omitted from this artifact.\n"
        f"- Real-Lina validation: `"
        f"{'VERIFIED' if report.get('real_lina_verified') is True else 'NOT VERIFIED'}`.\n"
    )


def _publish_historical_acceptance_report(
    directory: Path, report: Mapping[str, object]
) -> dict[str, object]:
    _preflight_artifact_directory(directory)
    json_path, markdown_path = _historical_artifact_paths(directory)
    serializable = dict(report)
    _atomic_write_text(
        json_path,
        json.dumps(serializable, indent=2, sort_keys=True, default=str) + "\n",
    )
    _atomic_write_text(markdown_path, _historical_acceptance_markdown(serializable))
    serializable["artifact_json"] = str(json_path)
    serializable["artifact_markdown"] = str(markdown_path)
    return serializable


def _load_committed_reconstruction_audit(
    configuration: AcceptanceConfiguration,
    *,
    session: Session,
    learning_session: LearningSession,
    segments: Sequence[LearningSegment],
) -> dict[str, object]:
    operation_id = _required_reconstruction_operation_id(learning_session.id)
    stage = _audit_stage_paths(configuration.artifact_directory, operation_id)
    if stage.pending_json_path.exists() or not stage.final_json_path.is_file():
        raise AcceptanceSafetyError(
            "Committed historical reconstruction audit is unavailable."
        )
    try:
        audit = json.loads(stage.final_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise AcceptanceSafetyError(
            "Committed historical reconstruction audit is unreadable."
        ) from None
    if not isinstance(audit, dict) or audit.get("publication_state") != "COMMITTED":
        raise AcceptanceSafetyError(
            "Committed historical reconstruction audit is invalid."
        )
    try:
        execution_id = UUID(str(audit["ai_execution_id"]))
    except (KeyError, TypeError, ValueError):
        raise AcceptanceSafetyError(
            "Committed historical reconstruction audit has invalid ledger lineage."
        ) from None
    _verified_reconstruction_execution(
        session.get(AIExecution, execution_id),
        learning_session=learning_session,
        operation_id=operation_id,
    )
    reported_segments = audit.get("segment_ids")
    expected_segments = {
        str(segment.sequence): str(segment.id) for segment in segments
    }
    if reported_segments != expected_segments:
        raise AcceptanceSafetyError(
            "Committed historical reconstruction audit does not match target Segments."
        )
    return {
        "operation_id": str(operation_id),
        "ai_execution_id": str(execution_id),
        "provider": "openai",
        "model": "gpt-5.6-luna",
        "segment_count": len(segments),
        "publication_state": "COMMITTED",
    }


def _preflight_historical_intelligence_target(
    configuration: AcceptanceConfiguration,
) -> tuple[dict[str, object], HistoricalSnapshot]:
    boundary = validate_database_boundary(
        configuration.source_database_url,
        configuration.target_database_url,
    )
    source_snapshot = _historical_snapshot(configuration.source_database_url)
    validate_historical_counts(source_snapshot.counts, location="historical-source")
    target_snapshot = _historical_snapshot(configuration.target_database_url)
    validate_historical_snapshots(
        source_snapshot,
        target_snapshot,
        location="historical-target",
    )
    revision = _target_alembic_revision(configuration.target_database_url)
    engine = create_engine(
        normalize_database_url(configuration.target_database_url), pool_pre_ping=True
    )
    try:
        with Session(engine) as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            learning_session, messages, _ = _ordered_messages(session)
            if learning_session.intelligence_pipeline != SESSION_FINALIZATION_PIPELINE:
                raise AcceptanceSafetyError(
                    "Historical target is not on segment-finalization-v1."
                )
            segments = list(
                session.scalars(
                    select(LearningSegment)
                    .where(LearningSegment.session_id == learning_session.id)
                    .order_by(LearningSegment.sequence, LearningSegment.id)
                )
            )
            if (
                not segments
                or any(message.segment_id is None for message in messages)
                or any(segment.closed_at is None for segment in segments)
                or len({message.segment_id for message in messages}) != len(segments)
            ):
                raise AcceptanceSafetyError(
                    "Historical target reconstruction is incomplete."
                )
            reconstruction = _load_committed_reconstruction_audit(
                configuration,
                session=session,
                learning_session=learning_session,
                segments=segments,
            )
    except AcceptanceSafetyError:
        raise
    except (OSError, SQLAlchemyError, TypeError, ValueError):
        raise AcceptanceSafetyError(
            "Historical target readiness inspection failed; details suppressed."
        ) from None
    finally:
        engine.dispose()
    return (
        {
            "source_database": boundary.source_identity.safe_label,
            "target_database": boundary.target_identity.safe_label,
            "target_alembic_revision": revision,
            "source_snapshot": _snapshot_report(source_snapshot),
            "target_snapshot": _snapshot_report(target_snapshot),
            "reconstruction": reconstruction,
            "source_write_operations": 0,
        },
        source_snapshot,
    )


def _close_and_ensure_historical_review_jobs(
    session_factory: sessionmaker[Session],
) -> list[UUID]:
    """Close only the target Session and idempotently ensure its Review jobs."""

    with session_factory.begin() as session:
        learning_session = session.get(
            LearningSession, HISTORICAL_SESSION_ID, with_for_update=True
        )
        if learning_session is None:
            raise AcceptanceSafetyError("Historical target Session is absent.")
        if learning_session.intelligence_pipeline != SESSION_FINALIZATION_PIPELINE:
            raise AcceptanceSafetyError(
                "Historical target Session has an unsupported pipeline."
            )
        controlled_policy = SessionLifecyclePolicy(
            version="full-system-acceptance-historical-v1",
            inactivity=timedelta(seconds=1),
            grace=timedelta(0),
        )
        controlled_now = max(
            datetime.now(UTC), controlled_policy.closes_at(learning_session.last_activity_at)
        )
        if learning_session.status == "OPEN":
            if not close_session_if_eligible(
                session,
                learning_session=learning_session,
                now=controlled_now,
                policy=controlled_policy,
            ):
                raise AcceptanceSafetyError(
                    "Controlled historical Session closure was not eligible."
                )
        elif learning_session.status != "CLOSED" or learning_session.closed_at is None:
            raise AcceptanceSafetyError(
                "Historical target Session has an unsupported lifecycle state."
            )
        reconcile_segments_for_session_close(
            session,
            learning_session=learning_session,
            closed_at=learning_session.closed_at or controlled_now,
        )
        segment_ids = [
            segment.id
            for segment in session.scalars(
                select(LearningSegment)
                .where(LearningSegment.session_id == learning_session.id)
                .order_by(LearningSegment.sequence, LearningSegment.id)
            )
            if is_segment_structurally_reviewable(
                session,
                learning_session=learning_session,
                segment=segment,
            )
        ]
        enqueue_session_intelligence_finalization_if_ready(
            session,
            learning_session=learning_session,
        )
        jobs = list(
            session.scalars(
                select(Job).where(Job.job_type == SEGMENT_LEARNING_REVIEW_JOB)
            )
        )
        _validate_historical_active_job_scope(
            jobs, session_id=learning_session.id
        )
        target_jobs = [
            job
            for job in jobs
            if isinstance(job.payload, dict)
            and job.payload.get("session_id") == str(learning_session.id)
        ]
        try:
            queued_segment_ids = {
                UUID(str(job.payload.get("segment_id"))) for job in target_jobs
            }
        except (TypeError, ValueError):
            raise AcceptanceSafetyError(
                "Historical Segment Review job lineage is invalid."
            ) from None
        if queued_segment_ids != set(segment_ids) or len(target_jobs) != len(segment_ids):
            raise AcceptanceSafetyError(
                "Historical Segment Review jobs do not exactly cover reviewable Segments."
            )
        if any(
            job.status in {JobStatus.FAILED.value, JobStatus.RUNNING.value}
            for job in target_jobs
        ):
            raise AcceptanceSafetyError(
                "Historical Segment Review job is failed or already running."
            )
        return [job.id for job in target_jobs]


def _scoped_registry(
    full_registry: JobHandlerRegistry, *, job_type: str
) -> JobHandlerRegistry:
    handler = full_registry.get(job_type)
    if handler is None:
        raise AcceptanceSafetyError(
            f"Required historical worker handler {job_type!r} is unavailable."
        )
    scoped = JobHandlerRegistry()
    scoped.register(job_type, handler)
    return scoped


def _run_exact_historical_jobs(
    session_factory: sessionmaker[Session],
    *,
    registry: JobHandlerRegistry,
    job_type: str,
    expected_job_ids: Sequence[UUID],
) -> list[dict[str, object]]:
    """Execute only the prevalidated target jobs through the normal worker."""

    worker_id = f"acceptance-{_historical_acceptance_operation_id()}"
    expected = set(expected_job_ids)
    while True:
        with session_factory() as session:
            jobs = list(
                session.scalars(select(Job).where(Job.job_type == job_type))
            )
            _validate_historical_active_job_scope(
                jobs, session_id=HISTORICAL_SESSION_ID
            )
            target_jobs = [
                job
                for job in jobs
                if isinstance(job.payload, dict)
                and job.payload.get("session_id") == str(HISTORICAL_SESSION_ID)
            ]
            if {job.id for job in target_jobs} != expected:
                raise AcceptanceSafetyError(
                    "Historical worker job set contains unexpected target jobs."
                )
            selected = [job for job in jobs if job.id in expected]
            if len(selected) != len(expected):
                raise AcceptanceSafetyError(
                    "Historical worker job set changed after preflight."
                )
            failed_or_running = [
                job
                for job in selected
                if job.status in {JobStatus.FAILED.value, JobStatus.RUNNING.value}
            ]
            if failed_or_running:
                raise AcceptanceSafetyError(
                    "Historical worker encountered a failed or concurrently running job."
                )
            pending = [job for job in selected if job.status == JobStatus.PENDING.value]
            if not pending:
                return [
                    {
                        "job_id": str(job.id),
                        "status": job.status,
                        "attempt_count": job.attempt_count,
                        "result": job.result if isinstance(job.result, dict) else {},
                    }
                    for job in selected
                ]
        status = run_once(
            session_factory,
            registry,
            worker_id=worker_id,
            now=datetime.now(UTC),
        )
        if status is not JobStatus.COMPLETED:
            raise AcceptanceSafetyError(
                f"Historical {job_type} worker execution failed closed."
            )


def _collect_completed_historical_reviews(
    session_factory: sessionmaker[Session],
    *,
    expected_segment_ids: Sequence[UUID],
) -> list[dict[str, object]]:
    expected = set(expected_segment_ids)
    with session_factory() as session:
        learning_session = session.get(LearningSession, HISTORICAL_SESSION_ID)
        if learning_session is None:
            raise AcceptanceSafetyError("Historical target Session is absent.")
        reviews = list(
            session.scalars(
                select(SegmentLearningReview)
                .where(
                    SegmentLearningReview.session_id == HISTORICAL_SESSION_ID,
                    SegmentLearningReview.segment_id.in_(expected),
                    SegmentLearningReview.schema_version
                    == SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
                    SegmentLearningReview.prompt_version
                    == SEGMENT_LEARNING_REVIEW_PROMPT_VERSION,
                    SegmentLearningReview.rubric_version == EVIDENCE_RUBRIC_VERSION,
                    SegmentLearningReview.review_policy_version
                    == SEGMENT_REVIEW_POLICY_VERSION,
                    SegmentLearningReview.provider == "openai",
                    SegmentLearningReview.model == "gpt-5.6-luna",
                )
                .order_by(SegmentLearningReview.segment_id)
            )
        )
        if len(reviews) != len(expected) or {review.segment_id for review in reviews} != expected:
            raise AcceptanceSafetyError(
                "Completed historical Reviews do not exactly cover required Segments."
            )
        report: list[dict[str, object]] = []
        for review in reviews:
            segment = session.get(LearningSegment, review.segment_id)
            if segment is None or segment.session_id != HISTORICAL_SESSION_ID:
                raise AcceptanceSafetyError(
                    "Historical Review Segment lineage is unavailable."
                )
            messages = list(
                session.scalars(
                    select(LearningMessage).where(
                        LearningMessage.session_id == HISTORICAL_SESSION_ID,
                        LearningMessage.segment_id == review.segment_id,
                    )
                )
            )
            finding_count = _validate_completed_review_sources(
                review,
                segment_message_roles={message.id: message.role for message in messages},
            )
            execution = _validate_segment_review_execution(
                review,
                execution=session.get(AIExecution, review.ai_execution_id),
                expected_student_id=learning_session.student_id,
                expected_segment_id=segment.id,
            )
            report.append(
                {
                    "segment_id": str(review.segment_id),
                    "segment_sequence": segment.sequence,
                    "segment_review_id": str(review.id),
                    "status": review.status,
                    "finding_count": finding_count,
                    "ai_execution_id": str(execution.id),
                    "operation_id": (
                        str(execution.operation_id)
                        if execution.operation_id is not None
                        else None
                    ),
                    "operation": execution.operation_type,
                    "task": execution.task,
                    "provider": execution.provider,
                    "model": execution.model,
                    "execution_success": execution.success,
                    "source_lineage_valid": True,
                }
            )
        return report


def _collect_historical_finalization(
    session_factory: sessionmaker[Session],
) -> dict[str, object]:
    with session_factory() as session:
        authorities = list(
            session.scalars(
                select(IntelligenceSessionAuthority).where(
                    IntelligenceSessionAuthority.session_id == HISTORICAL_SESSION_ID
                )
            )
        )
        if len(authorities) != 1:
            raise AcceptanceSafetyError(
                "Historical finalization did not produce exactly one Session authority."
            )
        authority = authorities[0]
        run = session.get(
            IntelligenceProcessingRun, authority.evidence_processing_run_id
        )
        if run is None or run.status != "COMPLETED":
            raise AcceptanceSafetyError(
                "Historical authority does not select one completed processing run."
            )
        scope = run.scope if isinstance(run.scope, dict) else {}
        if (
            scope.get("session_id") != str(HISTORICAL_SESSION_ID)
            or scope.get("intelligence_pipeline") != SESSION_FINALIZATION_PIPELINE
        ):
            raise AcceptanceSafetyError(
                "Historical processing run scope does not match the Session pipeline."
            )
        events = list(
            session.scalars(
                select(LearningEvent).where(
                    LearningEvent.processing_run_id == run.id,
                    LearningEvent.session_id == HISTORICAL_SESSION_ID,
                )
            )
        )
        evidence_count = int(
            session.scalar(
                select(func.count())
                .select_from(LearningEvidence)
                .join(LearningEvent, LearningEvent.id == LearningEvidence.event_id)
                .where(LearningEvent.processing_run_id == run.id)
            )
            or 0
        )
        reviews = {
            review.id: review
            for review in session.scalars(
                select(SegmentLearningReview).where(
                    SegmentLearningReview.session_id == HISTORICAL_SESSION_ID
                )
            )
        }
        withheld = 0
        for review in reviews.values():
            findings = review.output.get("findings") if isinstance(review.output, dict) else []
            if isinstance(findings, list):
                withheld += sum(
                    isinstance(finding, dict)
                    and finding.get("subject_alignment") != "SAME_AS_SESSION"
                    for finding in findings
                )
        for event in events:
            review = reviews.get(event.segment_review_id)
            findings = review.output.get("findings") if review is not None and isinstance(review.output, dict) else None
            index = event.segment_review_finding_index
            if (
                not isinstance(findings, list)
                or not isinstance(index, int)
                or index < 0
                or index >= len(findings)
                or event.segment_id != review.segment_id
            ):
                raise AcceptanceSafetyError(
                    "Historical Event provenance does not resolve to its Review Finding."
                )
            finding = findings[index]
            if (
                not isinstance(finding, dict)
                or finding.get("source_message_ids") != event.source_message_ids
                or finding.get("candidate_event_ids") != event.candidate_event_ids
            ):
                raise AcceptanceSafetyError(
                    "Historical Event source provenance differs from its Review Finding."
                )
        return {
            "authority_id": str(authority.id),
            "processing_run_id": str(run.id),
            "processing_run_status": run.status,
            "event_count": len(events),
            "evidence_count": evidence_count,
            "current_state_count": int(
                session.scalar(
                    select(func.count()).select_from(CurrentLearningState).where(
                        CurrentLearningState.processing_run_id == run.id
                    )
                )
                or 0
            ),
            "pattern_count": int(
                session.scalar(
                    select(func.count()).select_from(LearnerPattern).where(
                        LearnerPattern.processing_run_id == run.id
                    )
                )
                or 0
            ),
            "decision_view_count": int(
                session.scalar(
                    select(func.count()).select_from(DecisionView).where(
                        DecisionView.processing_run_id == run.id
                    )
                )
                or 0
            ),
            "card_count": int(
                session.scalar(
                    select(func.count()).select_from(LearnerIntelligenceCard).where(
                        LearnerIntelligenceCard.processing_run_id == run.id
                    )
                )
                or 0
            ),
            "withheld_finding_count": withheld,
            "candidate_free_event_count": sum(
                not event.candidate_event_ids for event in events
            ),
            "event_review_provenance_valid": True,
        }


def _historical_durable_state(
    session_factory: sessionmaker[Session],
) -> dict[str, object]:
    """Return non-secret durable/staged state after a fail-closed attempt."""

    try:
        with session_factory() as session:
            learning_session = session.get(LearningSession, HISTORICAL_SESSION_ID)
            if learning_session is None:
                return {
                    "inspection": "COMPLETE",
                    "historical_session_present": False,
                    "atomicity_verdict": "NO_HISTORICAL_SESSION",
                    "partial_session_activation_detected": None,
                    "selected_processing_run_id": None,
                }
            reviews = list(
                session.scalars(
                    select(SegmentLearningReview)
                    .where(SegmentLearningReview.session_id == HISTORICAL_SESSION_ID)
                    .order_by(SegmentLearningReview.created_at, SegmentLearningReview.id)
                )
            )
            review_rows: list[dict[str, object]] = []
            review_status_counts: dict[str, int] = {}
            staged_finding_count = 0
            withheld_finding_count = 0
            for review in reviews:
                findings = (
                    review.output.get("findings")
                    if isinstance(review.output, dict)
                    else None
                )
                finding_count = len(findings) if isinstance(findings, list) else 0
                withheld_count = (
                    sum(
                        isinstance(finding, dict)
                        and finding.get("subject_alignment") != "SAME_AS_SESSION"
                        for finding in findings
                    )
                    if isinstance(findings, list)
                    else 0
                )
                review_status_counts[review.status] = (
                    review_status_counts.get(review.status, 0) + 1
                )
                staged_finding_count += finding_count
                withheld_finding_count += withheld_count
                review_rows.append(
                    {
                        "id": str(review.id),
                        "segment_id": str(review.segment_id),
                        "status": review.status,
                        "finding_count": finding_count,
                        "withheld_finding_count": withheld_count,
                        "ai_execution_id": (
                            str(review.ai_execution_id)
                            if review.ai_execution_id is not None
                            else None
                        ),
                    }
                )
            authorities = list(
                session.scalars(
                    select(IntelligenceSessionAuthority).where(
                        IntelligenceSessionAuthority.session_id
                        == HISTORICAL_SESSION_ID
                    )
                )
            )
            authority_rows = [
                {
                    "id": str(authority.id),
                    "evidence_processing_run_id": str(
                        authority.evidence_processing_run_id
                    ),
                    "reprocess_run_id": (
                        str(authority.reprocess_run_id)
                        if authority.reprocess_run_id is not None
                        else None
                    ),
                }
                for authority in authorities
            ]
            events = list(
                session.scalars(
                    select(LearningEvent).where(
                        LearningEvent.session_id == HISTORICAL_SESSION_ID
                    )
                )
            )
            referenced_run_ids = {event.processing_run_id for event in events} | {
                authority.evidence_processing_run_id for authority in authorities
            }
            student_runs = list(
                session.scalars(
                    select(IntelligenceProcessingRun).where(
                        IntelligenceProcessingRun.student_id
                        == learning_session.student_id
                    )
                )
            )
            runs = [
                run
                for run in student_runs
                if (
                    isinstance(run.scope, dict)
                    and run.scope.get("session_id") == str(HISTORICAL_SESSION_ID)
                )
                or run.id in referenced_run_ids
            ]
            run_ids = {run.id for run in runs}
            evidence = (
                list(
                    session.scalars(
                        select(LearningEvidence).where(
                            LearningEvidence.event_id.in_([event.id for event in events])
                        )
                    )
                )
                if events
                else []
            )
            states = (
                list(
                    session.scalars(
                        select(CurrentLearningState).where(
                            CurrentLearningState.processing_run_id.in_(run_ids)
                        )
                    )
                )
                if run_ids
                else []
            )
            patterns = (
                list(
                    session.scalars(
                        select(LearnerPattern).where(
                            LearnerPattern.processing_run_id.in_(run_ids)
                        )
                    )
                )
                if run_ids
                else []
            )
            decisions = (
                list(
                    session.scalars(
                        select(DecisionView).where(
                            DecisionView.processing_run_id.in_(run_ids)
                        )
                    )
                )
                if run_ids
                else []
            )
            cards = (
                list(
                    session.scalars(
                        select(LearnerIntelligenceCard).where(
                            LearnerIntelligenceCard.processing_run_id.in_(run_ids)
                        )
                    )
                )
                if run_ids
                else []
            )
            jobs = list(
                session.scalars(
                    select(Job).where(
                        Job.job_type.in_(
                            (
                                SEGMENT_LEARNING_REVIEW_JOB,
                                SESSION_INTELLIGENCE_FINALIZE_JOB,
                            )
                        )
                    )
                )
            )
            job_rows = [
                {
                    "id": str(job.id),
                    "job_type": job.job_type,
                    "status": job.status,
                    "attempt_count": job.attempt_count,
                }
                for job in jobs
                if isinstance(job.payload, dict)
                and job.payload.get("session_id") == str(HISTORICAL_SESSION_ID)
            ]
            derived_counts = {
                "events": len(events),
                "evidence": len(evidence),
                "current_states": len(states),
                "patterns": len(patterns),
                "decision_views": len(decisions),
                "cards": len(cards),
            }
            snapshot: dict[str, object] = {
                "inspection": "COMPLETE",
                "historical_session_present": True,
                "reviews": review_rows,
                "review_status_counts": review_status_counts,
                "staged_finding_count": staged_finding_count,
                "withheld_finding_count": withheld_finding_count,
                "jobs": job_rows,
                "authorities": authority_rows,
                "processing_runs": [
                    {
                        "id": str(run.id),
                        "status": run.status,
                        "pipeline": (
                            run.scope.get("intelligence_pipeline")
                            if isinstance(run.scope, dict)
                            else None
                        ),
                    }
                    for run in runs
                ],
                "derived_counts": derived_counts,
                "derived_rows": {
                    "events": [
                        {
                            "id": str(event.id),
                            "processing_run_id": str(event.processing_run_id),
                            "segment_review_id": (
                                str(event.segment_review_id)
                                if event.segment_review_id is not None
                                else None
                            ),
                            "segment_review_finding_index": event.segment_review_finding_index,
                        }
                        for event in events
                    ],
                    "evidence_ids": [str(row.id) for row in evidence],
                    "current_state_ids": [str(row.id) for row in states],
                    "pattern_ids": [str(row.id) for row in patterns],
                    "decision_view_ids": [str(row.id) for row in decisions],
                    "card_ids": [str(row.id) for row in cards],
                },
            }
            snapshot.update(_derive_historical_atomicity(snapshot))
            return snapshot
    except Exception:  # noqa: BLE001 -- failure-state inspection is deliberately best effort.
        return {
            "inspection": "UNAVAILABLE",
            "atomicity_verdict": "INSPECTION_INCOMPLETE",
            "partial_session_activation_detected": None,
            "selected_processing_run_id": None,
        }


def run_historical_intelligence_acceptance(
    configuration: AcceptanceConfiguration,
    *,
    environment: Mapping[str, str] = os.environ,
) -> dict[str, object]:
    """Run real historical Reviews and deterministic activation on the isolated target."""

    _preflight_artifact_directory(configuration.artifact_directory)
    preflight, source_before = _preflight_historical_intelligence_target(configuration)
    settings = _provider_settings(configuration.target_database_url, environment)
    timeout_seconds = _acceptance_model_timeout_seconds(environment)
    engine = create_engine(
        normalize_database_url(configuration.target_database_url), pool_pre_ping=True
    )
    session_factory = sessionmaker(engine, expire_on_commit=False)
    try:
        segment_ids = _close_and_ensure_historical_review_jobs(session_factory)

        def segment_gateway_factory(session: Session) -> ModelGateway:
            provider = OpenAIResponsesProvider(
                api_key=settings.model_api_key.get_secret_value(),
                base_url=settings.model_base_url,
                timeout_seconds=timeout_seconds,
            )
            return create_segment_evidence_gateway(
                session,
                settings=settings,
                openai_provider=provider,
            )

        full_registry = JobHandlerRegistry()
        register_intelligence_handlers(
            full_registry,
            session_factory=session_factory,
            segment_evidence_gateway_factory=segment_gateway_factory,
        )
        with session_factory() as session:
            review_jobs = list(
                session.scalars(
                    select(Job).where(
                        Job.job_type == SEGMENT_LEARNING_REVIEW_JOB,
                        Job.payload["session_id"].astext == str(HISTORICAL_SESSION_ID),
                    )
                )
            )
        review_job_report = _run_exact_historical_jobs(
            session_factory,
            registry=_scoped_registry(
                full_registry, job_type=SEGMENT_LEARNING_REVIEW_JOB
            ),
            job_type=SEGMENT_LEARNING_REVIEW_JOB,
            expected_job_ids=[job.id for job in review_jobs],
        )
        review_report = _collect_completed_historical_reviews(
            session_factory,
            expected_segment_ids=segment_ids,
        )
        with session_factory.begin() as session:
            learning_session = session.get(
                LearningSession, HISTORICAL_SESSION_ID, with_for_update=True
            )
            if learning_session is None:
                raise AcceptanceSafetyError("Historical target Session is absent.")
            final_job = enqueue_session_intelligence_finalization_if_ready(
                session,
                learning_session=learning_session,
            )
            if final_job is None:
                raise AcceptanceSafetyError(
                    "Historical finalization job is not ready after completed Reviews."
                )
            final_job_id = final_job.id
        with session_factory() as session:
            final_jobs = list(
                session.scalars(
                    select(Job).where(Job.job_type == SESSION_INTELLIGENCE_FINALIZE_JOB)
                )
            )
            _validate_historical_active_job_scope(
                final_jobs, session_id=HISTORICAL_SESSION_ID
            )
        final_job_report = _run_exact_historical_jobs(
            session_factory,
            registry=_scoped_registry(
                full_registry, job_type=SESSION_INTELLIGENCE_FINALIZE_JOB
            ),
            job_type=SESSION_INTELLIGENCE_FINALIZE_JOB,
            expected_job_ids=[final_job_id],
        )
        finalization = _collect_historical_finalization(session_factory)
        target_after = _historical_snapshot(configuration.target_database_url)
        validate_historical_snapshots(
            source_before, target_after, location="historical-target-after"
        )
        source_after = _historical_snapshot(configuration.source_database_url)
        validate_historical_snapshots(
            source_before, source_after, location="historical-source-after"
        )
        return _publish_historical_acceptance_report(
            configuration.artifact_directory,
            {
                "mode": "HISTORICAL_INTELLIGENCE_ACCEPTANCE",
                "operation_id": str(_historical_acceptance_operation_id()),
                "historical_session_id": str(HISTORICAL_SESSION_ID),
                "status": "COMPLETED",
                "execution_taxonomy": "CODEX_REPORTED_REAL_MODEL_VERIFICATION",
                "real_luna_verified": bool(review_report)
                and len(review_report) == len(segment_ids)
                and all(
                    review.get("execution_success") is True
                    and review.get("provider") == "openai"
                    and review.get("model") == "gpt-5.6-luna"
                    and review.get("operation") == "segment_learning_review"
                    for review in review_report
                ),
                "database_end_to_end_verified": True,
                "real_lina_verified": False,
                "preflight": preflight,
                "segment_reviews": review_report,
                "review_jobs": review_job_report,
                "finalization_job": final_job_report,
                "finalization": finalization,
                "raw_message_fields_preserved": True,
                "source_write_operations": 0,
            },
        )
    except AcceptanceSafetyError as error:
        failure = {
            "mode": "HISTORICAL_INTELLIGENCE_ACCEPTANCE",
            "operation_id": str(_historical_acceptance_operation_id()),
            "historical_session_id": str(HISTORICAL_SESSION_ID),
            "status": "FAILED_CLOSED",
            "failure": str(error),
            "durable_state": _historical_durable_state(session_factory),
            "real_luna_verified": False,
            "database_end_to_end_verified": False,
            "real_lina_verified": False,
            "source_write_operations": 0,
        }
        artifact = _publish_historical_acceptance_report(
            configuration.artifact_directory, failure
        )
        raise AcceptanceSafetyError(
            "Historical intelligence acceptance failed closed; durable/staged state was recorded at "
            f"{artifact['artifact_json']}."
        ) from None
    except Exception:  # noqa: BLE001 -- redact unexpected provider/DB details in failure artifacts.
        failure = {
            "mode": "HISTORICAL_INTELLIGENCE_ACCEPTANCE",
            "operation_id": str(_historical_acceptance_operation_id()),
            "historical_session_id": str(HISTORICAL_SESSION_ID),
            "status": "FAILED_CLOSED",
            "failure": "Provider or database operation failed; details suppressed.",
            "durable_state": _historical_durable_state(session_factory),
            "real_luna_verified": False,
            "database_end_to_end_verified": False,
            "real_lina_verified": False,
            "source_write_operations": 0,
        }
        artifact = _publish_historical_acceptance_report(
            configuration.artifact_directory, failure
        )
        raise AcceptanceSafetyError(
            "Historical intelligence acceptance failed closed; durable/staged state was recorded at "
            f"{artifact['artifact_json']}."
        ) from None
    finally:
        engine.dispose()


def run_prepared_acceptance(
    configuration: AcceptanceConfiguration,
    *,
    environment: Mapping[str, str] = os.environ,
) -> dict[str, object]:
    isolation = prepare_isolated_target(configuration)
    report: dict[str, object] = {
        "isolation": isolation,
        "provider_execution": "DISABLED",
    }
    if configuration.execute_reconstruction:
        report["reconstruction"] = execute_real_reconstruction(
            configuration,
            environment=environment,
        )
        report["provider_execution"] = "REAL_MODEL_REQUESTED"
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-database-env-var",
        default=DEFAULT_SOURCE_DATABASE_ENV_VAR,
        help=(
            "Name of the process environment variable containing the source URL; "
            f"default: {DEFAULT_SOURCE_DATABASE_ENV_VAR}."
        ),
    )
    parser.add_argument(
        "--target-database-env-var",
        default=DEFAULT_TARGET_DATABASE_ENV_VAR,
        help=(
            "Name of the process environment variable containing the target URL; "
            f"default: {DEFAULT_TARGET_DATABASE_ENV_VAR}."
        ),
    )
    parser.add_argument("--artifact-directory", type=Path, required=True)
    parser.add_argument(
        "--execute-clone",
        action="store_true",
        help="Explicitly create and migrate the separate acceptance target.",
    )
    parser.add_argument(
        "--execute-reconstruction",
        action="store_true",
        help="After cloning, execute real openai/gpt-5.6-luna reconstruction through the Model Gateway.",
    )
    parser.add_argument(
        "--resume-reconstruction",
        action="store_true",
        help="Execute real reconstruction on an existing separately cloned and untouched target.",
    )
    parser.add_argument(
        "--recover-audit-operation-id",
        type=UUID,
        help="Publish a pending post-commit audit after verifying its target ledger lineage.",
    )
    parser.add_argument(
        "--run-historical-intelligence",
        action="store_true",
        help=(
            "Process the already reconstructed isolated target through real Segment Review "
            "jobs and deterministic Session finalization."
        ),
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    environment: Mapping[str, str] = os.environ,
) -> int:
    selected_argv = list(argv) if argv is not None else sys.argv[1:]
    forbidden = {"--source-database-url", "--target-database-url"}
    if any(
        argument.split("=", 1)[0] in forbidden
        or (
            "://" in argument
            and (
                "postgresql" in argument.casefold()
                or "postgres:" in argument.casefold()
            )
        )
        for argument in selected_argv
    ):
        print(
            "Acceptance stopped: Database URLs must be supplied through named environment variables.",
            file=sys.stderr,
        )
        return 2
    args = _parser().parse_args(selected_argv)
    try:
        source_database_url, target_database_url = _database_urls_from_environment(
            source_name=args.source_database_env_var,
            target_name=args.target_database_env_var,
            environment=environment,
        )
        configuration = AcceptanceConfiguration(
            source_database_url=source_database_url,
            target_database_url=target_database_url,
            artifact_directory=args.artifact_directory,
            execute_reconstruction=(
                args.execute_reconstruction or args.resume_reconstruction
            ),
        )
        if args.run_historical_intelligence and (
            args.execute_clone
            or args.execute_reconstruction
            or args.resume_reconstruction
            or args.recover_audit_operation_id
        ):
            raise AcceptanceSafetyError(
                "--run-historical-intelligence is mutually exclusive with clone, reconstruction, resume, and audit recovery modes."
            )
        if args.resume_reconstruction and (
            args.execute_clone
            or args.execute_reconstruction
            or args.recover_audit_operation_id
        ):
            raise AcceptanceSafetyError(
                "--resume-reconstruction is mutually exclusive with clone, reconstruction, and audit recovery modes."
            )
        if args.recover_audit_operation_id and (
            args.execute_clone or args.execute_reconstruction
        ):
            raise AcceptanceSafetyError(
                "Audit recovery cannot be combined with clone or reconstruction execution."
            )
        if args.execute_reconstruction and not args.execute_clone:
            raise AcceptanceSafetyError(
                "--execute-reconstruction requires --execute-clone."
            )
        if args.run_historical_intelligence:
            report = run_historical_intelligence_acceptance(
                configuration,
                environment=environment,
            )
        elif args.resume_reconstruction:
            report = resume_real_reconstruction(
                configuration,
                environment=environment,
            )
        elif args.recover_audit_operation_id:
            report = recover_staged_reconstruction_audit(
                configuration,
                operation_id=args.recover_audit_operation_id,
            )
        else:
            report = (
                run_prepared_acceptance(configuration, environment=environment)
                if args.execute_clone
                else provider_disabled_plan(configuration)
            )
    except AcceptanceSafetyError as error:
        print(f"Acceptance stopped: {error}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
