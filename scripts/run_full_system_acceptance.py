"""Prepare and run Lina's isolated full-system acceptance journey.

The default mode is a provider-disabled, no-write preflight. Database URLs are
resolved only from explicitly named process environment variables. Database
cloning and real-model reconstruction require separate explicit flags, while
credentials stay out of command arguments, errors, and generated artifacts.
"""

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
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from alembic.util.exc import CommandError
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError, SQLAlchemyError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    LearningMessage,
    LearningSegment,
    LearningSession,
    ModelTask,
)

HISTORICAL_SESSION_ID = UUID("8b1b647c-91ec-427e-b455-0adbca831101")
ACCEPTANCE_RECONSTRUCTION_VERSION = "acceptance-segment-reconstruction-v1"
ACCEPTANCE_RECONSTRUCTION_OPERATION = "full_system_acceptance_segment_reconstruction"
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
    except Exception:  # noqa: BLE001 -- provider/DB errors are redacted at this fail-closed CLI boundary.
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
        if args.resume_reconstruction:
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
