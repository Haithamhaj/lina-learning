from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Self
from uuid import NAMESPACE_URL, uuid4, uuid5

import pytest

from scripts.run_full_system_acceptance import (
    ACCEPTANCE_RECONSTRUCTION_OPERATION,
    EXPECTED_HISTORICAL_COUNTS,
    HISTORICAL_SESSION_ID,
    AcceptanceConfiguration,
    AcceptanceSafetyError,
    AuditStage,
    CommandSpec,
    HistoricalCounts,
    HistoricalSnapshot,
    ReconstructionValidationError,
    ResumeTargetState,
    SourceMessage,
    _acceptance_model_timeout_seconds,
    _commit_with_staged_audit,
    _create_acceptance_reconstruction_gateway,
    _database_urls_from_environment,
    _derive_historical_atomicity,
    _historical_acceptance_markdown,
    _historical_acceptance_operation_id,
    _migrate_target,
    _parser,
    _provider_settings,
    _publish_staged_audit,
    _required_reconstruction_operation_id,
    _select_current_historical_review_jobs,
    _stage_audit_artifact,
    _validate_completed_review_sources,
    _validate_historical_active_job_scope,
    _validate_resume_target_state,
    _validate_segment_review_execution,
    _verified_reconstruction_execution,
    build_clone_commands,
    build_reconstruction_payload,
    canonical_database_identity,
    execute_command,
    historical_message_manifest,
    main,
    prepare_isolated_target,
    provider_disabled_plan,
    redact_database_url,
    resume_real_reconstruction,
    validate_database_boundary,
    validate_historical_counts,
    validate_historical_snapshots,
    validate_reconstruction_output,
)
from services.intelligence.segment_reviews import SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
from services.platform.config import Settings
from services.platform.db.models import (
    AIExecution,
    LearningSegment,
    LearningSession,
    ModelTask,
)
from services.tutor.segment_lifecycle import SEGMENT_REVIEW_REQUEST_VERSION
from workers.intelligence_handlers import register_intelligence_handlers
from workers.job_worker import JobHandlerRegistry

SOURCE = "postgresql+psycopg://source_user:source-secret@db.example:5432/lina_source"
TARGET = "postgresql+psycopg://target_user:target-secret@db.example:5432/lina_acceptance_20260829_a1"


def _messages(count: int = 3) -> list[SourceMessage]:
    started = datetime(2026, 8, 29, tzinfo=UTC)
    return [
        SourceMessage(
            id=uuid4(),
            role="student" if index % 2 == 0 else "tutor",
            content=f"message {index}",
            created_at=started + timedelta(seconds=index),
            metadata={"index": index},
            ai_execution_id=uuid4(),
        )
        for index in range(count)
    ]


def test_database_identity_is_canonical_and_redacted() -> None:
    identity = canonical_database_identity(SOURCE)

    assert identity.host == "db.example"
    assert identity.port == 5432
    assert identity.database == "lina_source"
    assert identity.safe_label == "db.example:5432/lina_source"
    assert "source-secret" not in repr(identity)
    assert (
        redact_database_url(SOURCE)
        == "postgresql+psycopg://source_user:***@db.example:5432/lina_source"
    )


def test_cli_accepts_only_database_environment_variable_names(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    help_text = _parser().format_help()
    assert "--source-database-url" not in help_text
    assert "--target-database-url" not in help_text
    assert "--source-database-env-var" in help_text
    assert "--target-database-env-var" in help_text
    assert "--resume-reconstruction" in help_text

    result = main(
        [
            "--source-database-url",
            SOURCE,
            "--target-database-url",
            TARGET,
            "--artifact-directory",
            str(tmp_path),
        ],
        environment={},
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "source-secret" not in captured.out + captured.err
    assert "target-secret" not in captured.out + captured.err
    assert (
        "Database URLs must be supplied through named environment variables"
        in captured.err
    )

    result = main(
        [SOURCE, "--artifact-directory", str(tmp_path)],
        environment={},
    )
    captured = capsys.readouterr()
    assert result == 2
    assert "source-secret" not in captured.out + captured.err


def test_cli_reads_database_urls_from_named_environment_without_emitting_secrets(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = main(
        [
            "--artifact-directory",
            str(tmp_path),
            "--source-database-env-var",
            "ACCEPTANCE_SOURCE",
            "--target-database-env-var",
            "ACCEPTANCE_TARGET",
        ],
        environment={"ACCEPTANCE_SOURCE": SOURCE, "ACCEPTANCE_TARGET": TARGET},
    )
    captured = capsys.readouterr()

    assert result == 0
    assert "source-secret" not in captured.out + captured.err
    assert "target-secret" not in captured.out + captured.err
    assert '"provider_execution": "DISABLED"' in captured.out


def test_database_environment_lookup_reports_names_only() -> None:
    with pytest.raises(AcceptanceSafetyError) as captured:
        _database_urls_from_environment(
            source_name="ACCEPTANCE_SOURCE",
            target_name="ACCEPTANCE_TARGET",
            environment={"ACCEPTANCE_SOURCE": SOURCE},
        )

    assert "ACCEPTANCE_TARGET" in str(captured.value)
    assert "source-secret" not in str(captured.value)


def test_resume_mode_is_mutually_exclusive_with_clone_and_recovery(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    environment = {
        "LINA_ACCEPTANCE_SOURCE_DATABASE_URL": SOURCE,
        "LINA_ACCEPTANCE_TARGET_DATABASE_URL": TARGET,
    }
    result = main(
        [
            "--artifact-directory",
            str(tmp_path),
            "--resume-reconstruction",
            "--execute-clone",
        ],
        environment=environment,
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "mutually exclusive" in captured.err
    assert "source-secret" not in captured.err


def test_historical_intelligence_mode_is_explicit_and_mutually_exclusive(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    environment = {
        "LINA_ACCEPTANCE_SOURCE_DATABASE_URL": SOURCE,
        "LINA_ACCEPTANCE_TARGET_DATABASE_URL": TARGET,
    }

    assert "--run-historical-intelligence" in _parser().format_help()
    result = main(
        [
            "--artifact-directory",
            str(tmp_path),
            "--run-historical-intelligence",
            "--resume-reconstruction",
        ],
        environment=environment,
    )
    captured = capsys.readouterr()

    assert result == 2
    assert "mutually exclusive" in captured.err
    assert "source-secret" not in captured.out + captured.err
    assert "target-secret" not in captured.out + captured.err


def test_historical_intelligence_mode_routes_to_existing_target_runner_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed: dict[str, object] = {}

    def run(configuration: AcceptanceConfiguration, **_: object) -> dict[str, object]:
        observed["configuration"] = configuration
        return {"mode": "HISTORICAL_INTELLIGENCE_ACCEPTANCE"}

    monkeypatch.setattr(
        "scripts.run_full_system_acceptance.run_historical_intelligence_acceptance",
        run,
    )
    result = main(
        ["--artifact-directory", str(tmp_path), "--run-historical-intelligence"],
        environment={
            "LINA_ACCEPTANCE_SOURCE_DATABASE_URL": SOURCE,
            "LINA_ACCEPTANCE_TARGET_DATABASE_URL": TARGET,
        },
    )
    captured = capsys.readouterr()

    assert result == 0
    configuration = observed["configuration"]
    assert isinstance(configuration, AcceptanceConfiguration)
    assert configuration.execute_reconstruction is False
    assert "HISTORICAL_INTELLIGENCE_ACCEPTANCE" in captured.out
    assert "source-secret" not in captured.out + captured.err
    assert "target-secret" not in captured.out + captured.err


def test_historical_job_scope_refuses_claimable_jobs_for_other_sessions() -> None:
    target_session_id = HISTORICAL_SESSION_ID
    selected = SimpleNamespace(
        id=uuid4(),
        status="PENDING",
        payload={"session_id": str(target_session_id)},
    )
    copied_other = SimpleNamespace(
        id=uuid4(),
        status="PENDING",
        payload={"session_id": str(uuid4())},
    )

    with pytest.raises(AcceptanceSafetyError, match="other Sessions"):
        _validate_historical_active_job_scope(
            [selected, copied_other],
            session_id=target_session_id,
        )

    copied_other.status = "COMPLETED"
    _validate_historical_active_job_scope(
        [selected, copied_other],
        session_id=target_session_id,
    )


def test_historical_job_selection_preserves_prior_request_audit_and_uses_current_request_version() -> None:
    """Catches prior review jobs blocking an immutable current-version Review rerun."""

    prior = SimpleNamespace(
        payload={
            "session_id": str(HISTORICAL_SESSION_ID),
            "review_request_version": "segment-review-request-v1",
        }
    )
    current = SimpleNamespace(
        payload={
            "session_id": str(HISTORICAL_SESSION_ID),
            "review_request_version": "segment-review-request-v3",
        }
    )

    assert _select_current_historical_review_jobs(
        [prior, current], session_id=HISTORICAL_SESSION_ID
    ) == [current]
    assert SEGMENT_REVIEW_REQUEST_VERSION == "segment-review-request-v3"


def test_completed_review_sources_must_be_exact_segment_student_lineage() -> None:
    student_message_id = uuid4()
    tutor_message_id = uuid4()
    review = SimpleNamespace(
        status="COMPLETED",
        output={
            "version": SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
            "findings": [
                {
                    "source_message_ids": [str(student_message_id), str(tutor_message_id)],
                    "candidate_event_ids": [],
                    "subject_alignment": "SAME_AS_SESSION",
                }
            ],
        },
    )

    assert _validate_completed_review_sources(
        review,
        segment_message_roles={
            student_message_id: "student",
            tutor_message_id: "tutor",
        },
    ) == 1

    review.output["findings"][0]["source_message_ids"] = [str(uuid4())]
    with pytest.raises(AcceptanceSafetyError, match="source lineage"):
        _validate_completed_review_sources(
            review,
            segment_message_roles={student_message_id: "student"},
        )

    review.output = None
    with pytest.raises(AcceptanceSafetyError, match="strict schema"):
        _validate_completed_review_sources(
            review,
            segment_message_roles={student_message_id: "student"},
        )


def test_historical_acceptance_operation_identity_is_stable() -> None:
    assert _historical_acceptance_operation_id() == _historical_acceptance_operation_id()


def test_review_execution_requires_exact_production_segment_review_lineage() -> None:
    student_id = uuid4()
    segment_id = uuid4()
    review_id = uuid4()
    review = SimpleNamespace(
        id=review_id,
        student_id=student_id,
        session_id=HISTORICAL_SESSION_ID,
        segment_id=segment_id,
        ai_execution_id=uuid4(),
    )
    execution = SimpleNamespace(
        id=review.ai_execution_id,
        success=True,
        task=ModelTask.SEGMENT_EVIDENCE.value,
        provider="openai",
        model="gpt-5.6-luna",
        student_id=student_id,
        learning_session_id=HISTORICAL_SESSION_ID,
        operation_type="full_system_acceptance_segment_reconstruction",
        operation_id=uuid4(),
    )

    with pytest.raises(AcceptanceSafetyError, match="ledger lineage"):
        _validate_segment_review_execution(
            review,
            execution=execution,
            expected_student_id=student_id,
            expected_segment_id=segment_id,
        )

    execution.operation_type = "segment_learning_review"
    execution.operation_id = uuid5(
        NAMESPACE_URL, f"segment-learning-review:{review_id}"
    )
    assert (
        _validate_segment_review_execution(
            review,
            execution=execution,
            expected_student_id=student_id,
            expected_segment_id=segment_id,
        )
        is execution
    )


def test_failed_review_snapshot_proves_no_activation_only_from_exact_rows() -> None:
    snapshot = {
        "reviews": [
            {
                "id": str(uuid4()),
                "status": "FAILED",
                "finding_count": 0,
                "withheld_finding_count": 0,
            }
        ],
        "jobs": [
            {
                "id": str(uuid4()),
                "job_type": "SEGMENT_LEARNING_REVIEW",
                "status": "PENDING",
            }
        ],
        "authorities": [],
        "processing_runs": [],
        "derived_counts": {
            "events": 0,
            "evidence": 0,
            "current_states": 0,
            "patterns": 0,
            "decision_views": 0,
            "cards": 0,
        },
    }

    assert _derive_historical_atomicity(snapshot) == {
        "atomicity_verdict": "NO_SESSION_ACTIVATION",
        "partial_session_activation_detected": False,
        "selected_processing_run_id": None,
    }


def test_post_finalization_reporting_failure_reports_durable_atomic_activation() -> None:
    run_id = uuid4()
    snapshot = {
        "authorities": [
            {"evidence_processing_run_id": str(run_id), "reprocess_run_id": None}
        ],
        "processing_runs": [
            {
                "id": str(run_id),
                "status": "COMPLETED",
                "pipeline": "segment-finalization-v1",
            }
        ],
        "derived_counts": {
            "events": 3,
            "evidence": 3,
            "current_states": 2,
            "patterns": 1,
            "decision_views": 1,
            "cards": 1,
        },
    }

    assert _derive_historical_atomicity(snapshot) == {
        "atomicity_verdict": "COMPLETE_SESSION_ACTIVATION_PRESENT",
        "partial_session_activation_detected": False,
        "selected_processing_run_id": str(run_id),
    }


def test_completed_run_with_wrong_pipeline_is_not_accepted_as_atomic_activation() -> None:
    run_id = uuid4()
    snapshot = {
        "authorities": [
            {"evidence_processing_run_id": str(run_id), "reprocess_run_id": None}
        ],
        "processing_runs": [
            {
                "id": str(run_id),
                "status": "COMPLETED",
                "pipeline": "legacy-session-evidence-v1",
            }
        ],
        "derived_counts": {
            "events": 0,
            "evidence": 0,
            "current_states": 0,
            "patterns": 0,
            "decision_views": 0,
            "cards": 0,
        },
    }

    result = _derive_historical_atomicity(snapshot)
    assert result["atomicity_verdict"] == "INCONSISTENT_OR_PARTIAL_ACTIVATION"
    assert result["partial_session_activation_detected"] is True


def test_failed_markdown_renders_durable_review_job_and_activation_evidence() -> None:
    run_id = uuid4()
    report = {
        "historical_session_id": str(HISTORICAL_SESSION_ID),
        "status": "FAILED_CLOSED",
        "real_luna_verified": False,
        "database_end_to_end_verified": False,
        "real_lina_verified": False,
        "durable_state": {
            "reviews": [
                {"id": str(uuid4()), "status": "COMPLETED"},
                {"id": str(uuid4()), "status": "COMPLETED"},
                {"id": str(uuid4()), "status": "COMPLETED"},
                {"id": str(uuid4()), "status": "FAILED"},
            ],
            "review_status_counts": {"COMPLETED": 3, "FAILED": 1},
            "staged_finding_count": 7,
            "withheld_finding_count": 2,
            "jobs": [
                {"job_type": "SEGMENT_LEARNING_REVIEW", "status": "COMPLETED"},
                {"job_type": "SEGMENT_LEARNING_REVIEW", "status": "PENDING"},
            ],
            "authorities": [],
            "processing_runs": [],
            "derived_counts": {
                "events": 0,
                "evidence": 0,
                "current_states": 0,
                "patterns": 0,
                "decision_views": 0,
                "cards": 0,
            },
            "atomicity_verdict": "NO_SESSION_ACTIVATION",
            "selected_processing_run_id": None,
        },
    }

    markdown = _historical_acceptance_markdown(report)

    assert "Durable Segment Reviews completed: `3`" in markdown
    assert 'Review statuses: `{"COMPLETED": 3, "FAILED": 1}`' in markdown
    assert "Staged / withheld Findings: `7 / 2`" in markdown
    assert "SEGMENT_LEARNING_REVIEW:COMPLETED=1" in markdown
    assert "SEGMENT_LEARNING_REVIEW:PENDING=1" in markdown
    assert "Events / Evidence: `0 / 0`" in markdown
    assert "Activation verdict: `NO_SESSION_ACTIVATION`" in markdown
    assert "Real Luna verified: `false`" in markdown
    assert "Execution taxonomy: `NOT VERIFIED`" in markdown
    assert "Codex-executed real-model verification" not in markdown
    assert str(run_id) not in markdown


def test_segment_review_worker_uses_explicit_isolated_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "not-valid-settings-json")
    student_id = uuid4()
    segment_id = uuid4()
    learning_session = SimpleNamespace(
        id=HISTORICAL_SESSION_ID,
        student_id=student_id,
    )
    segment = SimpleNamespace(
        id=segment_id,
        session_id=HISTORICAL_SESSION_ID,
        closed_at=datetime(2026, 8, 29, tzinfo=UTC),
        closure_reason="SESSION_CLOSED",
    )
    isolated_settings = Settings(
        _env_file=None,
        _env_prefix="__LINA_TEST_EXPLICIT_SETTINGS__",
        segment_review_context_capacity=12_345,
    )
    captured: dict[str, object] = {}

    class FakeSession:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def get(
            self, model: object, identity: object, **_: object
        ) -> SimpleNamespace | None:
            if model is LearningSession and identity == HISTORICAL_SESSION_ID:
                return learning_session
            if model is LearningSegment and identity == segment_id:
                return segment
            return None

        def commit(self) -> None:
            captured["committed"] = True

    class FakeSessionFactory:
        def __call__(self) -> FakeSession:
            return FakeSession()

    review = SimpleNamespace(id=uuid4(), status="COMPLETED")

    def review_segment(*_: object, **kwargs: object) -> SimpleNamespace:
        captured["settings"] = kwargs.get("settings")
        return SimpleNamespace(review=review, finding_count=0, model_called=True)

    monkeypatch.setattr(
        "workers.intelligence_handlers.review_completed_segment",
        review_segment,
    )
    monkeypatch.setattr(
        "workers.intelligence_handlers.enqueue_session_intelligence_finalization_if_ready",
        lambda *_args, **_kwargs: None,
    )
    registry = JobHandlerRegistry()
    register_intelligence_handlers(
        registry,
        session_factory=FakeSessionFactory(),  # type: ignore[arg-type]
        segment_evidence_gateway_factory=lambda _: object(),  # type: ignore[arg-type,return-value]
        segment_review_settings=isolated_settings,
    )
    handler = registry.get("SEGMENT_LEARNING_REVIEW")
    assert handler is not None

    result = handler(
        SimpleNamespace(
            payload={
                "student_id": str(student_id),
                "session_id": str(HISTORICAL_SESSION_ID),
                "segment_id": str(segment_id),
                "review_request_version": SEGMENT_REVIEW_REQUEST_VERSION,
                "closed_at": segment.closed_at.isoformat(),
                "closure_reason": segment.closure_reason,
            }
        )
    )

    assert captured["settings"] is isolated_settings
    assert isolated_settings.segment_review_context_capacity == 12_345
    assert captured["committed"] is True
    assert result["review_status"] == "COMPLETED"


def test_orphan_derived_rows_are_reported_as_possible_partial_activation() -> None:
    snapshot = {
        "authorities": [],
        "processing_runs": [{"id": str(uuid4()), "status": "RUNNING"}],
        "derived_counts": {
            "events": 1,
            "evidence": 0,
            "current_states": 0,
            "patterns": 0,
            "decision_views": 0,
            "cards": 0,
        },
    }

    result = _derive_historical_atomicity(snapshot)
    assert result["atomicity_verdict"] == "INCONSISTENT_OR_PARTIAL_ACTIVATION"
    assert result["partial_session_activation_detected"] is True


def test_resume_preflight_revalidates_snapshots_and_never_runs_clone_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuration = AcceptanceConfiguration(
        source_database_url=SOURCE,
        target_database_url=TARGET,
        artifact_directory=tmp_path,
        execute_reconstruction=True,
    )
    snapshot = HistoricalSnapshot(
        counts=EXPECTED_HISTORICAL_COUNTS,
        raw_message_manifest_sha256="a" * 64,
    )
    calls: list[str] = []
    monkeypatch.setattr(
        "scripts.run_full_system_acceptance._historical_snapshot",
        lambda url: (
            calls.append("source-snapshot" if url == SOURCE else "target-snapshot")
            or snapshot
        ),
    )
    monkeypatch.setattr(
        "scripts.run_full_system_acceptance._target_alembic_revision",
        lambda _: calls.append("alembic-head") or "head",
    )
    monkeypatch.setattr(
        "scripts.run_full_system_acceptance._read_resume_target_state",
        lambda *_: (
            calls.append("target-state")
            or ResumeTargetState(
                intelligence_pipeline="legacy-session-evidence-v1",
                segment_count=0,
                assigned_message_count=0,
                pending_audit_exists=False,
                committed_audit_exists=False,
            )
        ),
    )
    monkeypatch.setattr(
        "scripts.run_full_system_acceptance.execute_real_reconstruction",
        lambda *_, **__: calls.append("real-reconstruction") or {"ok": True},
    )
    monkeypatch.setattr(
        "scripts.run_full_system_acceptance.execute_command",
        lambda _: calls.append("command"),
    )

    report = resume_real_reconstruction(configuration, environment={})

    assert report["reconstruction"] == {"ok": True}
    assert calls == [
        "source-snapshot",
        "target-snapshot",
        "alembic-head",
        "target-state",
        "real-reconstruction",
    ]


def test_resume_stops_before_schema_state_or_provider_when_target_manifest_differs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuration = AcceptanceConfiguration(
        source_database_url=SOURCE,
        target_database_url=TARGET,
        artifact_directory=tmp_path,
        execute_reconstruction=True,
    )
    source_snapshot = HistoricalSnapshot(
        counts=EXPECTED_HISTORICAL_COUNTS,
        raw_message_manifest_sha256="a" * 64,
    )
    target_snapshot = HistoricalSnapshot(
        counts=EXPECTED_HISTORICAL_COUNTS,
        raw_message_manifest_sha256="b" * 64,
    )
    calls: list[str] = []

    def snapshot(url: str) -> HistoricalSnapshot:
        calls.append("source" if url == SOURCE else "target")
        return source_snapshot if url == SOURCE else target_snapshot

    monkeypatch.setattr(
        "scripts.run_full_system_acceptance._historical_snapshot",
        snapshot,
    )
    monkeypatch.setattr(
        "scripts.run_full_system_acceptance.execute_real_reconstruction",
        lambda *_, **__: calls.append("provider"),
    )

    with pytest.raises(AcceptanceSafetyError, match="raw Message manifest"):
        resume_real_reconstruction(configuration, environment={})

    assert calls == ["source", "target"]


@pytest.mark.parametrize(
    "state",
    [
        ResumeTargetState("segment-finalization-v1", 0, 0, False, False),
        ResumeTargetState("legacy-session-evidence-v1", 1, 0, False, False),
        ResumeTargetState("legacy-session-evidence-v1", 0, 1, False, False),
        ResumeTargetState("legacy-session-evidence-v1", 0, 0, True, False),
        ResumeTargetState("legacy-session-evidence-v1", 0, 0, False, True),
    ],
)
def test_resume_refuses_unsafe_existing_target_state(state: ResumeTargetState) -> None:
    with pytest.raises(AcceptanceSafetyError, match="resume refused"):
        _validate_resume_target_state(state)


def test_provider_settings_ignore_unrelated_inherited_project_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "not-valid-settings-json")
    monkeypatch.setenv("APP_ENV", "production")
    explicit_environment = {
        "MODEL_PROVIDER": "openai",
        "MODEL_NAME": "gpt-5.6-luna",
        "MODEL_API_KEY": "provider-secret",
    }

    settings = _provider_settings(TARGET, explicit_environment)

    assert settings.model_provider == "openai"
    assert settings.model_name == "gpt-5.6-luna"
    assert settings.database_url == TARGET
    assert settings.allowed_origins == ["http://localhost:5000"]
    assert "provider-secret" not in repr(settings)


def test_acceptance_model_timeout_default_and_valid_override() -> None:
    assert _acceptance_model_timeout_seconds({}) == 120.0
    assert (
        _acceptance_model_timeout_seconds(
            {"LINA_ACCEPTANCE_MODEL_TIMEOUT_SECONDS": "180"}
        )
        == 180.0
    )


@pytest.mark.parametrize("value", ["invalid", "29", "301", "30.5", ""])
def test_acceptance_model_timeout_refuses_invalid_or_out_of_range_values(
    value: str,
) -> None:
    with pytest.raises(AcceptanceSafetyError, match="between 30 and 300"):
        _acceptance_model_timeout_seconds(
            {"LINA_ACCEPTANCE_MODEL_TIMEOUT_SECONDS": value}
        )


def test_acceptance_gateway_injects_scoped_provider_timeout() -> None:
    settings = _provider_settings(
        TARGET,
        {
            "MODEL_PROVIDER": "openai",
            "MODEL_NAME": "gpt-5.6-luna",
            "MODEL_API_KEY": "provider-secret",
        },
    )
    observed: dict[str, object] = {}
    provider = object()
    gateway = object()

    def provider_factory(**kwargs: object) -> object:
        observed["provider_api_key_received"] = (
            kwargs.pop("api_key") == "provider-secret"
        )
        observed["provider_kwargs"] = kwargs
        return provider

    def gateway_factory(*args: object, **kwargs: object) -> object:
        observed["gateway_args"] = args
        observed["gateway_kwargs"] = kwargs
        return gateway

    selected_gateway, timeout = _create_acceptance_reconstruction_gateway(
        object(),
        settings=settings,
        environment={"LINA_ACCEPTANCE_MODEL_TIMEOUT_SECONDS": "240"},
        gateway_factory=gateway_factory,
        provider_factory=provider_factory,
    )

    assert selected_gateway is gateway
    assert timeout == 240.0
    assert observed["provider_api_key_received"] is True
    assert observed["provider_kwargs"]["timeout_seconds"] == 240.0
    assert observed["gateway_kwargs"]["openai_provider"] is provider
    assert observed["gateway_kwargs"]["settings"] is settings
    assert "provider-secret" not in repr(observed)


def test_equal_source_and_target_are_refused_without_leaking_credentials() -> None:
    same_target = "postgresql://other-user:other-secret@DB.EXAMPLE/lina_source"

    with pytest.raises(AcceptanceSafetyError) as captured:
        validate_database_boundary(SOURCE, same_target)

    assert "source-secret" not in str(captured.value)
    assert "other-secret" not in str(captured.value)
    assert (
        "source and target database identities are equal" in str(captured.value).lower()
    )


def test_localhost_aliases_are_the_same_canonical_database_identity() -> None:
    source = "postgresql://source:secret@localhost:5432/lina_source"
    target = "postgresql://target:other@127.0.0.1/lina_source"

    with pytest.raises(AcceptanceSafetyError, match="identities are equal"):
        validate_database_boundary(source, target)


@pytest.mark.parametrize(
    "target",
    [
        "postgresql://u:p@localhost/lina_learning_test",
        "postgresql://u:p@localhost/lina",
        "postgresql://u:p@localhost/lina_acceptance_" + "x" * 64,
        "sqlite:///lina_acceptance_20260829.db",
    ],
)
def test_target_must_be_a_unique_marked_postgresql_acceptance_database(
    target: str,
) -> None:
    with pytest.raises(AcceptanceSafetyError):
        validate_database_boundary(SOURCE, target)


def test_clone_commands_use_source_only_for_dump_and_keep_passwords_out_of_argv(
    tmp_path: Path,
) -> None:
    boundary = validate_database_boundary(SOURCE, TARGET)
    commands = build_clone_commands(boundary, dump_path=tmp_path / "source.dump")

    assert [command.purpose for command in commands] == [
        "source_dump",
        "target_create",
        "target_restore",
    ]
    assert commands[0].argv[0] == "pg_dump"
    assert "source-secret" not in " ".join(commands[0].argv)
    assert commands[0].environment == {"PGPASSWORD": "source-secret"}
    assert all("lina_source" not in " ".join(command.argv) for command in commands[1:])
    assert all("target-secret" not in " ".join(command.argv) for command in commands)
    assert all(command.argv[0] != "psql" for command in commands)
    assert all("--no-password" in command.argv for command in commands)
    assert "source-secret" not in repr(commands[0])


def test_command_failure_suppresses_stderr_and_secret_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise OSError("source-secret")

    monkeypatch.setattr("scripts.run_full_system_acceptance.subprocess.run", fail)
    command = CommandSpec(
        purpose="source_dump",
        argv=("pg_dump", "--dbname", "lina_source"),
        environment={"PGPASSWORD": "source-secret"},
    )

    with pytest.raises(AcceptanceSafetyError) as captured:
        execute_command(command)

    assert "source-secret" not in str(captured.value)
    assert captured.value.__cause__ is None


def test_child_command_receives_only_allowlisted_and_explicit_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, str] = {}

    def succeed(*args: object, **kwargs: object) -> None:
        del args
        observed.update(kwargs["env"])

    monkeypatch.setenv("UNRELATED_SENTINEL_SECRET", "must-not-propagate")
    monkeypatch.setattr("scripts.run_full_system_acceptance.subprocess.run", succeed)

    execute_command(
        CommandSpec(
            purpose="source_dump",
            argv=("pg_dump",),
            environment={"PGPASSWORD": "source-secret"},
        )
    )

    assert observed["PGPASSWORD"] == "source-secret"
    assert "PATH" in observed
    assert "UNRELATED_SENTINEL_SECRET" not in observed


def test_historical_counts_must_match_the_fixed_source_contract() -> None:
    validate_historical_counts(EXPECTED_HISTORICAL_COUNTS, location="source-before")

    with pytest.raises(AcceptanceSafetyError, match="source-before.*expected"):
        validate_historical_counts(
            HistoricalCounts(
                messages=144, student_messages=73, tutor_messages=71, candidates=38
            ),
            location="source-before",
        )


@pytest.mark.parametrize(
    "changed_field",
    ["id", "role", "content", "metadata", "ai_execution_id", "created_at"],
)
def test_historical_manifest_rejects_raw_record_drift_with_matching_counts(
    changed_field: str,
) -> None:
    source_messages = _messages()
    if changed_field == "id":
        replacement: object = uuid4()
    elif changed_field == "role":
        replacement = "observer"
    elif changed_field == "content":
        replacement = "changed raw content"
    elif changed_field == "metadata":
        replacement = {"changed": True}
    elif changed_field == "ai_execution_id":
        replacement = uuid4()
    else:
        replacement = source_messages[1].created_at + timedelta(microseconds=1)
    target_messages = list(source_messages)
    target_messages[1] = replace(target_messages[1], **{changed_field: replacement})
    source = HistoricalSnapshot(
        counts=EXPECTED_HISTORICAL_COUNTS,
        raw_message_manifest_sha256=historical_message_manifest(source_messages),
    )
    target = HistoricalSnapshot(
        counts=EXPECTED_HISTORICAL_COUNTS,
        raw_message_manifest_sha256=historical_message_manifest(target_messages),
    )

    with pytest.raises(AcceptanceSafetyError, match="raw Message manifest"):
        validate_historical_snapshots(
            source,
            target,
            location="target-after-migration",
        )


def test_historical_manifest_rejects_order_drift_with_matching_counts() -> None:
    source_messages = _messages()

    with pytest.raises(ReconstructionValidationError, match="chronologically ordered"):
        historical_message_manifest(list(reversed(source_messages)))


def test_reconstruction_output_must_assign_every_message_once_in_exact_order() -> None:
    messages = _messages()
    output = {
        "version": "acceptance-segment-reconstruction-v1",
        "assignments": [
            {
                "message_id": str(messages[0].id),
                "segment_sequence": 1,
                "boundary_reason": "Conversation begins.",
            },
            {
                "message_id": str(messages[1].id),
                "segment_sequence": 1,
                "boundary_reason": None,
            },
            {
                "message_id": str(messages[2].id),
                "segment_sequence": 2,
                "boundary_reason": "Meaning changes.",
            },
        ],
    }

    validated = validate_reconstruction_output(output, messages=messages)

    assert [item.message_id for item in validated.assignments] == [
        message.id for message in messages
    ]
    assert [item.segment_sequence for item in validated.assignments] == [1, 1, 2]

    duplicate = dict(output)
    duplicate["assignments"] = [*output["assignments"][:-1], output["assignments"][0]]
    with pytest.raises(ReconstructionValidationError):
        validate_reconstruction_output(duplicate, messages=messages)

    skipped_sequence = dict(output)
    skipped_sequence["assignments"] = [
        output["assignments"][0],
        output["assignments"][1],
        {
            "message_id": str(messages[2].id),
            "segment_sequence": 3,
            "boundary_reason": "Skip.",
        },
    ]
    with pytest.raises(ReconstructionValidationError):
        validate_reconstruction_output(skipped_sequence, messages=messages)


def test_reconstruction_rejects_tutor_first_or_new_segment_on_tutor() -> None:
    messages = _messages()
    tutor_first = [replace(messages[0], role="tutor"), messages[1], messages[2]]
    all_one_segment = {
        "version": "acceptance-segment-reconstruction-v1",
        "assignments": [
            {
                "message_id": str(message.id),
                "segment_sequence": 1,
                "boundary_reason": "Conversation begins." if index == 0 else None,
            }
            for index, message in enumerate(tutor_first)
        ],
    }
    with pytest.raises(ReconstructionValidationError, match="Student message"):
        validate_reconstruction_output(all_one_segment, messages=tutor_first)

    new_on_tutor = {
        "version": "acceptance-segment-reconstruction-v1",
        "assignments": [
            {
                "message_id": str(messages[0].id),
                "segment_sequence": 1,
                "boundary_reason": "Conversation begins.",
            },
            {
                "message_id": str(messages[1].id),
                "segment_sequence": 2,
                "boundary_reason": "Invalid Tutor-only start.",
            },
            {
                "message_id": str(messages[2].id),
                "segment_sequence": 3,
                "boundary_reason": "Student resumes.",
            },
        ],
    }
    with pytest.raises(ReconstructionValidationError, match="Student message"):
        validate_reconstruction_output(new_on_tutor, messages=messages)


def test_reconstruction_payload_is_complete_strict_and_has_auditable_lineage() -> None:
    messages = _messages()
    payload = build_reconstruction_payload(messages=messages, session_id=uuid4())

    assert payload["operation"] == ACCEPTANCE_RECONSTRUCTION_OPERATION
    assert [item["id"] for item in payload["source_messages"]] == [
        str(message.id) for message in messages
    ]
    assert [item["content"] for item in payload["source_messages"]] == [
        message.content for message in messages
    ]
    assert payload["response_schema"]["name"] == "acceptance_segment_reconstruction_v1"
    schema = payload["response_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["ReconstructionAssignment"]["additionalProperties"] is False
    assert set(schema["$defs"]["ReconstructionAssignment"]["required"]) == {
        "message_id",
        "segment_sequence",
        "boundary_reason",
    }
    assert "keyword" not in payload["instructions"].casefold()
    assert "regex" not in payload["instructions"].casefold()

    with pytest.raises(ReconstructionValidationError, match="chronologically ordered"):
        build_reconstruction_payload(
            messages=list(reversed(messages)), session_id=uuid4()
        )


def test_alembic_migration_uses_explicit_environment_from_an_empty_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[CommandSpec] = []

    def inspect(command: CommandSpec) -> None:
        assert command.working_directory.is_dir()
        assert not (command.working_directory / ".env").exists()
        observed.append(command)

    monkeypatch.setattr("scripts.run_full_system_acceptance.execute_command", inspect)

    _migrate_target(TARGET)

    assert len(observed) == 1
    assert observed[0].purpose == "target_migrate"
    assert observed[0].argv[-3:] == (
        str(Path(__file__).parents[1] / "alembic.ini"),
        "upgrade",
        "head",
    )
    assert observed[0].environment["DATABASE_URL"] == TARGET
    assert "target-secret" not in repr(observed[0])


def test_equal_identity_stops_preparation_before_database_or_command_activity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    activity: list[str] = []
    monkeypatch.setattr(
        "scripts.run_full_system_acceptance._historical_snapshot",
        lambda _: activity.append("database"),
    )
    configuration = AcceptanceConfiguration(
        source_database_url=TARGET,
        target_database_url=TARGET,
        artifact_directory=tmp_path,
    )

    with pytest.raises(AcceptanceSafetyError, match="identities are equal"):
        prepare_isolated_target(
            configuration,
            command_runner=lambda _: activity.append("command"),
        )

    assert activity == []


def test_verified_reconstruction_ledger_requires_exact_route_and_lineage() -> None:
    student_id = uuid4()
    session_id = uuid4()
    operation_id = _required_reconstruction_operation_id(session_id)
    learning_session = LearningSession(
        id=session_id,
        student_id=student_id,
        subject="MATH",
        status="CLOSED",
    )
    execution = AIExecution(
        id=uuid4(),
        task=ModelTask.SEGMENT_EVIDENCE.value,
        provider="openai",
        model="gpt-5.6-luna",
        latency_ms=1,
        success=True,
        operation_id=operation_id,
        operation_type=ACCEPTANCE_RECONSTRUCTION_OPERATION,
        student_id=student_id,
        learning_session_id=session_id,
    )

    assert (
        _verified_reconstruction_execution(
            execution,
            learning_session=learning_session,
            operation_id=operation_id,
        )
        is execution
    )

    execution.provider = "fixture"
    with pytest.raises(AcceptanceSafetyError, match="ledger lineage"):
        _verified_reconstruction_execution(
            execution,
            learning_session=learning_session,
            operation_id=operation_id,
        )


def test_provider_disabled_plan_never_constructs_or_calls_a_gateway(
    tmp_path: Path,
) -> None:
    configuration = AcceptanceConfiguration(
        source_database_url=SOURCE,
        target_database_url=TARGET,
        artifact_directory=tmp_path,
        execute_reconstruction=False,
    )
    calls: list[str] = []

    plan = provider_disabled_plan(
        configuration, gateway_factory=lambda _: calls.append("gateway")
    )

    assert calls == []
    assert plan["provider_execution"] == "DISABLED"
    assert plan["source_database"] == "db.example:5432/lina_source"
    assert plan["target_database"] == "db.example:5432/lina_acceptance_20260829_a1"
    assert "source-secret" not in repr(plan)
    assert "target-secret" not in repr(plan)


def test_staging_failure_rolls_back_and_pending_audit_can_be_published(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Transaction:
        def __init__(self) -> None:
            self.committed = False
            self.rolled_back = False

        def __enter__(self) -> None:
            return None

        def __exit__(
            self, error_type: object, error: object, traceback: object
        ) -> bool:
            del error, traceback
            self.committed = error_type is None
            self.rolled_back = error_type is not None
            return False

    class FakeSession:
        def __init__(self) -> None:
            self.transaction = Transaction()

        def begin(self) -> Transaction:
            return self.transaction

    fake_session = FakeSession()

    def fail_stage(audit: dict[str, object]) -> AuditStage:
        del audit
        raise OSError("disk full")

    with pytest.raises(OSError, match="disk full"):
        _commit_with_staged_audit(
            fake_session,
            operation=lambda: {"operation_id": str(uuid4())},
            stager=fail_stage,
        )

    assert fake_session.transaction.rolled_back is True
    assert fake_session.transaction.committed is False

    audit = {
        "operation_id": str(uuid4()),
        "historical_session_id": str(uuid4()),
        "provider": "openai",
        "model": "gpt-5.6-luna",
        "ai_execution_id": str(uuid4()),
        "assignments": [],
    }
    stage = _stage_audit_artifact(tmp_path, audit)
    assert (
        json.loads(stage.pending_json_path.read_text())["publication_state"]
        == "PENDING_DATABASE_COMMIT"
    )
    assert not stage.final_json_path.exists()
    module = __import__(
        "scripts.run_full_system_acceptance",
        fromlist=["_atomic_write_text"],
    )
    real_atomic_write = module._atomic_write_text

    def fail_publish(path: Path, content: str) -> None:
        del path, content
        raise OSError("rename failed")

    monkeypatch.setattr(
        "scripts.run_full_system_acceptance._atomic_write_text",
        fail_publish,
    )
    with pytest.raises(OSError, match="rename failed"):
        _publish_staged_audit(stage)
    assert stage.pending_json_path.exists()
    assert not stage.final_json_path.exists()

    monkeypatch.setattr(
        "scripts.run_full_system_acceptance._atomic_write_text",
        real_atomic_write,
    )
    _publish_staged_audit(stage)
    assert not stage.pending_json_path.exists()
    assert (
        json.loads(stage.final_json_path.read_text())["publication_state"]
        == "COMMITTED"
    )
