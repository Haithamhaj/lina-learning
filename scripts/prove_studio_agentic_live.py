"""Explicit real-provider proof for Tutor-led Agentic Canvas.

The harness is intentionally inert unless ``--live`` is supplied. Evidence is
identifier/digest/contract metadata only: no prompt, Tutor text, child content,
secret, provider URL, image bytes, or model chain-of-thought is written.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Callable
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from services.model_gateway.factory import create_tutor_gateway
from services.platform.config.settings import Settings
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    Job,
    LearningMessage,
    ModelTask,
    StudioCanvasSpecialistRun,
    StudioEvent,
    StudioScene,
    StudioStudentInteraction,
    StudioTutorObservation,
)
from services.studio.agent.orchestrator import (
    AgenticCanvasCompositionResult,
    compose_canvas_scene_with_trace,
)
from services.studio.agentic_canvas import AgenticCanvasSceneV1
from services.studio.canvas_brief import CanvasBriefV1, audit_canvas_brief
from services.studio.process_production_acceptance import agentic_scene_contract
from services.studio.tutor_context import StudioTutorWorkspaceContext
from services.tutor.runtime import build_tutor_model_payload


class _EvidenceSession:
    """Non-durable audit sink preserving the Model Gateway call boundary."""

    def __init__(self) -> None:
        self.executions: list[object] = []

    def add(self, execution: object) -> None:
        self.executions.append(execution)

    def flush(self) -> None:
        for execution in self.executions:
            if getattr(execution, "id", None) is None:
                execution.id = uuid4()


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _record(case_id: str, *, passed: bool, status: str = "RUN", **metadata: object) -> dict[str, object]:
    return {"case_id": case_id, "status": status, "passed": passed, **metadata}


class LiveEvidenceRecorder:
    """Atomically preserve bounded live evidence after every completed case."""

    def __init__(self, *, output: Path, model: str) -> None:
        self.output = output
        self.model = model
        self.results: list[dict[str, object]] = []

    def _write(
        self,
        *,
        run_status: str,
        all_required_passed: bool,
        failure: dict[str, object] | None = None,
    ) -> dict[str, object]:
        evidence: dict[str, object] = {
            "proof": "STUDIO-AGENTIC-01",
            "schema_version": "studio-agentic-live-proof-v1",
            "model": self.model,
            "run_status": run_status,
            "all_required_passed": all_required_passed,
            "results": self.results,
        }
        if failure is not None:
            evidence["failure"] = failure
        self.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.output.with_suffix(f"{self.output.suffix}.tmp")
        temporary.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.output)
        return evidence

    def start(self) -> None:
        self.results = []
        self._write(run_status="RUNNING", all_required_passed=False)

    def sync(self, results: list[dict[str, object]]) -> None:
        self.results = [dict(item) for item in results]
        self._write(run_status="RUNNING", all_required_passed=False)

    def record(self, result: dict[str, object]) -> None:
        self.results.append(dict(result))
        self._write(run_status="RUNNING", all_required_passed=False)

    def fail(self, error: BaseException) -> dict[str, object]:
        last_case_id = self.results[-1].get("case_id") if self.results else None
        return self._write(
            run_status="FAILED",
            all_required_passed=False,
            failure={
                "exception_type": type(error).__name__,
                "last_completed_case_id": last_case_id,
            },
        )

    def finish(self, results: list[dict[str, object]]) -> dict[str, object]:
        self.results = [dict(item) for item in results]
        case_ids = {item.get("case_id") for item in self.results if item.get("passed") is True}
        all_required_passed = case_ids == {f"LIVE-{index:02d}" for index in range(1, 13)}
        return self._write(
            run_status="COMPLETED",
            all_required_passed=all_required_passed,
        )


def _append_result(
    results: list[dict[str, object]],
    result: dict[str, object],
    on_progress: Callable[[list[dict[str, object]]], None] | None,
) -> None:
    results.append(result)
    if on_progress is not None:
        on_progress(results)


def _sync_results(
    results: list[dict[str, object]],
    on_progress: Callable[[list[dict[str, object]]], None] | None,
) -> None:
    if on_progress is not None:
        on_progress(results)


def _tutor_brief(
    settings: Settings,
    question: str,
    *,
    subject: str,
    locale: str,
) -> tuple[CanvasBriefV1, dict[str, object]]:
    session = _EvidenceSession()
    gateway = create_tutor_gateway(session, settings=settings)  # type: ignore[arg-type]
    workspace = StudioTutorWorkspaceContext(
        runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=0,
        snapshot_sequence=0, current_scene_id=None, current_scene_version=None,
        active_subject_key=subject, active_activity_key=None, state_payload={},
        unseen_events=(), observation_id=None,
    )
    result = gateway.execute(
        ModelTask.TUTOR,
        build_tutor_model_payload(
            question=question,
            student_core_context={"age_years": 10, "grade_level": 5},
            studio_context=workspace,
            workspace_subject_key=subject,
        ),
    )
    audit = audit_canvas_brief(
        result.output.get("canvas_brief"),
        allowed_source_references=set(),
        safety_allows=True,
    )
    if audit.get("status") != "ADMITTED":
        raw_brief = result.output.get("canvas_brief")
        validation_summary: list[dict[str, object]] = []
        try:
            CanvasBriefV1.model_validate(raw_brief)
        except ValidationError as error:
            validation_summary = error.errors(include_input=False, include_url=False)
        raise RuntimeError(
            json.dumps(
                {
                    "code": "LIVE_TUTOR_BRIEF_NOT_ADMITTED",
                    "audit_status": audit.get("status"),
                    "reason_code": audit.get("reason_code"),
                    "validation": validation_summary,
                },
                separators=(",", ":"),
            )
        )
    brief = CanvasBriefV1.model_validate(audit.get("brief"))
    return brief, {
        "tutor_execution_id": str(result.execution_id),
        "brief_digest": audit["brief_digest"],
        "locale": locale,
    }


async def _compose(settings: Settings, brief: CanvasBriefV1) -> AgenticCanvasCompositionResult:
    assert settings.model_api_key is not None
    return await compose_canvas_scene_with_trace(
        brief=brief,
        api_key=settings.model_api_key.get_secret_value(),
        model=settings.model_name,
        base_url=settings.model_base_url,
    )


def _agent_metadata(composition: AgenticCanvasCompositionResult) -> dict[str, object]:
    """Keep only bounded execution evidence; raw tool inputs and outputs are forbidden."""

    return {
        "sdk_trace_id": composition.sdk_trace_id,
        "selected_tools": list(composition.selected_tools),
        "tool_call_count": composition.tool_call_count,
        "usage": dict(composition.usage),
        "tool_statuses": [
            {
                "name": call.name,
                "call_id": call.call_id,
                "status": call.status,
                "input_digest": call.input_digest,
                "output_digest": call.output_digest,
                "produced_block_ids": list(call.produced_block_ids),
            }
            for call in composition.tool_calls
        ],
    }


def _scene_metadata(scene: AgenticCanvasSceneV1, brief: CanvasBriefV1) -> dict[str, object]:
    contract = agentic_scene_contract(scene, brief.model_dump(mode="json"))
    block_types = [block.type for block in scene.blocks]
    return {
        "scene_contract": scene.version,
        "scene_digest": _digest(scene.model_dump(mode="json")),
        "studio_subject": contract["subject_key"],
        "semantic_subject": scene.subject_key,
        "block_types": block_types,
    }


def _durable_studio_evidence(settings: Settings, run_id: UUID) -> dict[str, object]:
    """Read bounded evidence from the actual Studio Run and worker Job result."""

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL_REQUIRED_FOR_DURABLE_LIVE_EVIDENCE")
    engine = create_engine(normalize_database_url(settings.database_url))
    try:
        with Session(engine) as session:
            run = session.get(StudioCanvasSpecialistRun, run_id)
            if run is None or run.job_id is None:
                raise RuntimeError("STUDIO_RUN_NOT_FOUND")
            job = session.get(Job, run.job_id)
            scene = session.get(StudioScene, run.scene_id) if run.scene_id is not None else None
            result = job.result if job is not None and isinstance(job.result, dict) else {}
            trace = run.agent_execution_metadata if isinstance(run.agent_execution_metadata, dict) else {}
            selected_tools = trace.get("selected_tools")
            tool_call_count = trace.get("tool_call_count")
            if (
                result.get("run_id") != str(run.id)
                or not isinstance(run.sdk_trace_id, str)
                or trace.get("proposal_digest") != run.proposal_digest
                or not isinstance(selected_tools, list)
                or not all(isinstance(name, str) for name in selected_tools)
                or type(tool_call_count) is not int
            ):
                raise RuntimeError("DURABLE_AGENT_TRACE_MISSING")
            interaction = session.scalars(
                select(StudioStudentInteraction)
                .where(StudioStudentInteraction.studio_runtime_id == run.studio_runtime_id)
                .order_by(StudioStudentInteraction.created_at.desc())
            ).first()
            source_event = None
            if interaction is not None:
                source_event = session.get(StudioEvent, interaction.source_event_id)
                if (
                    source_event is None
                    or scene is None
                    or source_event.scene_id != scene.id
                    or source_event.actor != "STUDENT"
                    or source_event.action_key is None
                ):
                    interaction = None
            observation = (
                session.scalars(
                    select(StudioTutorObservation)
                    .where(
                        StudioTutorObservation.studio_runtime_id == run.studio_runtime_id,
                        StudioTutorObservation.student_interaction_id == interaction.id,
                    )
                    .order_by(StudioTutorObservation.created_at.desc())
                ).first()
                if interaction is not None
                else None
            )
            # LIVE-11 requires an update genuinely emitted by the same Primary
            # Tutor turn that completed the Canvas interaction.  A later,
            # unrelated Run in the runtime is not sufficient evidence.
            tutor_message = None
            if interaction is not None and interaction.tutor_message_id is not None:
                candidate = session.get(LearningMessage, interaction.tutor_message_id)
                payload = candidate.payload if candidate is not None and isinstance(candidate.payload, dict) else {}
                if (
                    candidate is not None
                    and candidate.role == "tutor"
                    and candidate.ai_execution_id == interaction.ai_execution_id
                    and payload.get("turn_origin") == "STUDIO_INTERACTION"
                    and payload.get("student_interaction_id") == str(interaction.id)
                    and payload.get("source_studio_event_id") == str(interaction.source_event_id)
                ):
                    tutor_message = candidate
            update_run = None
            update_message = tutor_message
            if update_message is not None:
                update_audit = (
                    update_message.payload.get("agentic_canvas")
                    if isinstance(update_message.payload, dict)
                    else None
                )
                if (
                    update_message is not None
                    and update_message.role == "tutor"
                    and isinstance(update_audit, dict)
                    and update_audit.get("status") == "ADMITTED"
                ):
                    update_run = session.scalars(
                        select(StudioCanvasSpecialistRun).where(
                            StudioCanvasSpecialistRun.studio_runtime_id == run.studio_runtime_id,
                            StudioCanvasSpecialistRun.source_message_id == update_message.id,
                            StudioCanvasSpecialistRun.base_scene_id == scene.id,
                        )
                    ).first()

            successor = None
            superseded = None
            if update_run is not None and update_run.status == "SUPERSEDED":
                failure = update_run.failure_metadata
                successor_digest = (
                    failure.get("successor_order_digest")
                    if isinstance(failure, dict)
                    and failure.get("code") == "SUPERSEDED_BY_NEWER_AGENTIC_CANVAS_BRIEF"
                    else None
                )
                if isinstance(successor_digest, str):
                    successor = session.scalars(
                        select(StudioCanvasSpecialistRun).where(
                            StudioCanvasSpecialistRun.studio_runtime_id == run.studio_runtime_id,
                            StudioCanvasSpecialistRun.order_digest == successor_digest,
                            StudioCanvasSpecialistRun.created_at > update_run.created_at,
                        )
                    ).first()
                    if successor is not None:
                        superseded = update_run
            return {
                "run_id": str(run.id),
                "scene_id": None if scene is None else str(scene.id),
                "scene_status": None if scene is None else scene.status,
                "proposal_digest": run.proposal_digest,
                "sdk_trace_id": run.sdk_trace_id,
                "usage": trace.get("usage"),
                "tool_calls": trace.get("tool_calls"),
                "selected_tools": selected_tools,
                "tool_call_count": tool_call_count,
                "interaction_id": None if interaction is None else str(interaction.id),
                "interaction_status": None if interaction is None else interaction.status,
                "action_key": None if source_event is None else source_event.action_key,
                "tutor_message_id": None if tutor_message is None else str(tutor_message.id),
                "observation_status": None if observation is None else observation.status,
                "observation_execution_id": (
                    None
                    if observation is None or observation.ai_execution_id is None
                    else str(observation.ai_execution_id)
                ),
                "tutor_execution_id": (
                    None
                    if interaction is None or interaction.ai_execution_id is None
                    else str(interaction.ai_execution_id)
                ),
                "update_run_id": None if update_run is None else str(update_run.id),
                "successor_run_id": None if successor is None else str(successor.id),
                "superseded_run_id": None if superseded is None else str(superseded.id),
            }
    finally:
        engine.dispose()


async def run_live(
    settings: Settings,
    *,
    durable_run_id: UUID | None = None,
    on_progress: Callable[[list[dict[str, object]]], None] | None = None,
) -> dict[str, object]:
    results: list[dict[str, object]] = []

    math_brief, math_lineage = _tutor_brief(
        settings,
        "Please open Canvas and show me why 0.407 is smaller than 0.47 without using a prepared exercise.",
        subject="MATH",
        locale="en",
    )
    _append_result(results, _record("LIVE-01", passed=True, **math_lineage), on_progress)
    math_composition = await _compose(settings, math_brief)
    math_scene = math_composition.scene
    math_metadata = _scene_metadata(math_scene, math_brief)
    _append_result(results, _record("LIVE-02", passed=math_scene.subject_key == "MATH", **math_metadata), on_progress)
    _append_result(results, _record(
        "LIVE-03",
        passed=math_composition.tool_call_count >= 2 and len(math_composition.selected_tools) >= 2,
        **_agent_metadata(math_composition),
    ), on_progress)

    live_cases = (
        ("LIVE-04", "Open Canvas for this Physics question about motion: a cyclist travels 3.6 kilometres while a runner travels 2500 metres. Preserve both physical distance quantities and their units, convert them exactly, and show their comparison as a clear visual relationship.", "PHYSICS", "en", 0, {"convert_units"}),
        ("LIVE-05", "Please use Canvas to build a visual cycle with at least five named stages for water moving through evaporation, condensation, clouds, precipitation, collection, and return flow.", "SCIENCE", "en", 5, {"create_diagram"}),
        ("LIVE-06", "افتح Canvas وساعدني بصريًا في ترتيب مراحل دورة الماء، واجعل النص عربيًا واضحًا ثم أضف مساحة أرتب فيها المراحل بنفسي.", "ARABIC", "ar", 0, {"create_text_interaction"}),
    )
    for case_id, question, subject, locale, minimum_elements, required_tools in live_cases:
        try:
            brief, lineage = _tutor_brief(settings, question, subject=subject, locale=locale)
            composition = await _compose(settings, brief)
            scene = composition.scene
            element_count = max((len(block.elements) for block in scene.blocks), default=0)
            passed = (
                (case_id != "LIVE-04" or brief.subject_key == "PHYSICS")
                and scene.subject_key == brief.subject_key
                and element_count >= minimum_elements
                and required_tools.issubset(composition.selected_tools)
            )
            if case_id == "LIVE-06":
                passed = passed and brief.direction == "rtl"
            _append_result(results, _record(
                case_id,
                passed=passed,
                element_count=element_count,
                **lineage,
                **_scene_metadata(scene, brief),
                **_agent_metadata(composition),
            ), on_progress)
        except Exception as error:  # noqa: BLE001 - each live case must record and continue
            _append_result(results, _record(case_id, passed=False, status="FAILED", reason_code=type(error).__name__), on_progress)

    hosted_cases = (
        (
            "LIVE-07",
            "Open Canvas for a science explanation that requires one original child-safe illustrative image of sunlight helping a small plant grow. Show organic leaf shapes, irregular soil texture, and natural light that a symbolic diagram or simple geometric shapes cannot faithfully express, alongside one concise typed explanation.",
            "SCIENCE",
            "en",
            "image_generation",
        ),
        (
            "LIVE-08",
            "Open Canvas for an exact bounded data investigation. Starting at 2, calculate the first 200 values of this recurrence: when a value is odd, the next is (3 times it plus 1) divided by 2; otherwise the next is half of it. Find the maximum, count the odd and even transitions, and compare the first and last 20 values as a typed visual summary without showing executable code.",
            "MATH",
            "en",
            "code_interpreter",
        ),
    )
    for case_id, question, subject, locale, required_tool in hosted_cases:
        try:
            brief, lineage = _tutor_brief(settings, question, subject=subject, locale=locale)
            composition = await _compose(settings, brief)
            scene_payload = composition.scene.model_dump(mode="json")
            serialized = json.dumps(scene_payload, ensure_ascii=False)
            passed = (
                required_tool in composition.selected_tools
                and (case_id != "LIVE-07" or len(composition.generated_images) == 1)
                and "code_interpreter_call" not in serialized
                and "image_generation_call" not in serialized
                and "base64" not in serialized.lower()
            )
            _append_result(results, _record(
                case_id,
                passed=passed,
                generated_image_count=len(composition.generated_images),
                **lineage,
                **_scene_metadata(composition.scene, brief),
                **_agent_metadata(composition),
            ), on_progress)
        except Exception as error:  # noqa: BLE001 - each live case must record and continue
            _append_result(results, _record(case_id, passed=False, status="FAILED", reason_code=type(error).__name__), on_progress)

    durable = None
    if durable_run_id is not None:
        try:
            durable = _durable_studio_evidence(settings, durable_run_id)
        except RuntimeError:
            durable = None
    if durable is None:
        _append_result(results, _record("LIVE-09", passed=False, status="NOT_RUN", reason_code="DURABLE_STUDIO_INTERACTION_REQUIRED"), on_progress)
        _append_result(results, _record("LIVE-10", passed=False, status="NOT_RUN", reason_code="DURABLE_ACTIVE_CANVAS_CHAT_REQUIRED"), on_progress)
        _append_result(results, _record("LIVE-11", passed=False, status="NOT_RUN", reason_code="DURABLE_TUTOR_UPDATE_AND_STALE_FENCE_REQUIRED"), on_progress)
    else:
        trace_passed = durable["tool_call_count"] >= 2 and len(durable["selected_tools"]) >= 2
        results[2] = _record("LIVE-03", passed=trace_passed, **{
            key: durable[key] for key in ("run_id", "scene_id", "proposal_digest", "sdk_trace_id", "selected_tools", "tool_call_count", "usage", "tool_calls")
        })
        _sync_results(results, on_progress)
        interaction_passed = (
            durable["interaction_status"] == "COMPLETED"
            and durable["action_key"] is not None
            and durable["tutor_message_id"] is not None
            and durable["observation_status"] == "COMMITTED"
            and durable["tutor_execution_id"] is not None
            and durable["observation_execution_id"] == durable["tutor_execution_id"]
        )
        _append_result(results, _record("LIVE-09", passed=interaction_passed, **{
            key: durable[key] for key in ("run_id", "scene_id", "interaction_id", "action_key", "interaction_status", "observation_status", "tutor_message_id", "tutor_execution_id")
        }), on_progress)
        _append_result(results, _record("LIVE-10", passed=interaction_passed and durable["scene_status"] == "ACTIVE", run_id=durable["run_id"], scene_id=durable["scene_id"], active_canvas=durable["scene_status"] == "ACTIVE", chat_execution_id=durable["tutor_execution_id"]), on_progress)
        update_passed = (
            durable["update_run_id"] is not None
            and durable["successor_run_id"] is not None
            and durable["superseded_run_id"] == durable["update_run_id"]
        )
        _append_result(results, _record("LIVE-11", passed=update_passed, run_id=durable["run_id"], update_run_id=durable["update_run_id"], successor_run_id=durable["successor_run_id"], superseded_run_id=durable["superseded_run_id"], update_requested=durable["update_run_id"] is not None, stale_fence_observed=durable["superseded_run_id"] == durable["update_run_id"]), on_progress)
    replayed = AgenticCanvasSceneV1.model_validate(json.loads(json.dumps(math_scene.model_dump(mode="json"))))
    _append_result(results, _record("LIVE-12", passed=replayed == math_scene, scene_contract=replayed.version, scene_digest=_digest(replayed.model_dump(mode="json"))), on_progress)
    return {
        "proof": "STUDIO-AGENTIC-01",
        "schema_version": "studio-agentic-live-proof-v1",
        "model": settings.model_name,
        "all_required_passed": all(item["passed"] for item in results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Authorize real provider calls for this invocation.")
    parser.add_argument("--output", type=Path, default=Path("output/studio-agentic-live-proof.json"))
    parser.add_argument("--env-file", type=Path, default=None, help="Optional explicit server dotenv path.")
    parser.add_argument("--studio-run-id", type=UUID, default=None, help="Optional actual Studio run used for durable LIVE-03 and LIVE-09 through LIVE-11 evidence.")
    args = parser.parse_args()
    if not args.live:
        raise SystemExit("Refusing provider calls without explicit --live.")
    settings = Settings(_env_file=args.env_file) if args.env_file is not None else Settings()
    if settings.model_api_key is None or settings.model_name == "mock":
        raise SystemExit("Configured MODEL_API_KEY and a real MODEL_NAME are required.")
    recorder = LiveEvidenceRecorder(output=args.output, model=settings.model_name)
    recorder.start()
    try:
        run_result = asyncio.run(
            run_live(
                settings,
                durable_run_id=args.studio_run_id,
                on_progress=recorder.sync,
            )
        )
    except BaseException as error:
        recorder.fail(error)
        print(
            json.dumps(
                {
                    "proof": "STUDIO-AGENTIC-01",
                    "status": "FAILED",
                    "exception_type": type(error).__name__,
                    "evidence_path": str(args.output),
                },
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        raise
    evidence = recorder.finish(run_result["results"])
    print(json.dumps({
        "proof": evidence["proof"],
        "all_required_passed": evidence["all_required_passed"],
        "results": [{"case_id": item["case_id"], "status": item["status"], "passed": item["passed"]} for item in evidence["results"]],
        "evidence_path": str(args.output),
    }, separators=(",", ":")))
    if not evidence["all_required_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
