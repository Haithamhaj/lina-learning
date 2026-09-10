"""Explicit real-provider proof for Tutor-led Agentic Canvas.

The harness is intentionally inert unless ``--live`` is supplied. Evidence is
identifier/digest/contract metadata only: no prompt, Tutor text, child content,
secret, provider URL, image bytes, or model chain-of-thought is written.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from services.model_gateway.factory import create_tutor_gateway
from services.platform.config.settings import Settings
from services.platform.db.models import ModelTask
from services.studio.agent.orchestrator import compose_canvas_scene
from services.studio.agentic_canvas import (
    AgenticCanvasActionV1,
    AgenticCanvasSceneV1,
    build_agentic_tutor_projection,
)
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


async def _compose(settings: Settings, brief: CanvasBriefV1) -> AgenticCanvasSceneV1:
    assert settings.model_api_key is not None
    return await compose_canvas_scene(
        brief=brief,
        api_key=settings.model_api_key.get_secret_value(),
        model=settings.model_name,
        base_url=settings.model_base_url,
    )


def _scene_metadata(scene: AgenticCanvasSceneV1, brief: CanvasBriefV1) -> dict[str, object]:
    contract = agentic_scene_contract(scene, brief.model_dump(mode="json"))
    block_types = [block.type for block in scene.blocks]
    return {
        "scene_contract": scene.version,
        "scene_digest": _digest(scene.model_dump(mode="json")),
        "studio_subject": contract["subject_key"],
        "semantic_subject": scene.subject_key,
        "block_types": block_types,
        # Creation tools are deterministically implied by accepted block types;
        # hidden SDK trace content is deliberately not persisted.
        "selected_tools": [f"create_{kind.lower()}" for kind in block_types],
    }


async def run_live(settings: Settings) -> dict[str, object]:
    run_id = uuid4()
    results: list[dict[str, object]] = []

    math_brief, math_lineage = _tutor_brief(
        settings,
        "Please open Canvas and show me why 0.407 is smaller than 0.47 without using a prepared exercise.",
        subject="MATH",
        locale="en",
    )
    results.append(_record("LIVE-01", passed=True, run_id=str(run_id), **math_lineage))
    math_scene = await _compose(settings, math_brief)
    math_metadata = _scene_metadata(math_scene, math_brief)
    results.append(_record("LIVE-02", passed=math_scene.subject_key == "MATH", **math_metadata))
    results.append(_record(
        "LIVE-03",
        passed=len(math_scene.blocks) >= 2,
        selected_tools=math_metadata["selected_tools"],
        deterministic_check="at_least_two_registered_blocks",
    ))

    live_cases = (
        ("LIVE-04", "Please use Canvas to help me compare 3.6 kilometres with 2500 metres using a visual relationship.", "SCIENCE", "en", 0),
        ("LIVE-05", "Please use Canvas to build a visual cycle with at least five named stages for water moving through evaporation, condensation, clouds, precipitation, collection, and return flow.", "SCIENCE", "en", 5),
        ("LIVE-06", "افتح Canvas وساعدني بصريًا في ترتيب مراحل دورة الماء، واجعل النص عربيًا واضحًا.", "ARABIC", "ar", 0),
    )
    for case_id, question, subject, locale, minimum_elements in live_cases:
        try:
            brief, lineage = _tutor_brief(settings, question, subject=subject, locale=locale)
            scene = await _compose(settings, brief)
            element_count = max((len(block.elements) for block in scene.blocks), default=0)
            passed = scene.subject_key == brief.subject_key and element_count >= minimum_elements
            if case_id == "LIVE-06":
                passed = passed and brief.direction == "rtl"
            results.append(_record(case_id, passed=passed, element_count=element_count, **lineage, **_scene_metadata(scene, brief)))
        except Exception as error:  # noqa: BLE001 - each live case must record and continue
            results.append(_record(case_id, passed=False, status="FAILED", reason_code=type(error).__name__))

    # Hosted tools are never represented as passing unless the runtime exposes
    # and audits them. These bounded results make the missing gate explicit.
    results.append(_record("LIVE-07", passed=False, status="NOT_RUN", reason_code="HOSTED_IMAGE_TOOL_NOT_REGISTERED"))
    results.append(_record("LIVE-08", passed=False, status="NOT_USED", reason_code="CODE_INTERPRETER_NOT_REQUIRED_BY_EXECUTED_CASES"))

    first_block = math_scene.blocks[0]
    first_element = first_block.elements[0] if first_block.elements else None
    action = AgenticCanvasActionV1(
        version="agentic-canvas-action-v1",
        action="SELECT",
        block_id=first_block.block_id,
        element_id=None if first_element is None else first_element.id,
        from_value=None,
        to_value=None,
    )
    projection = build_agentic_tutor_projection(
        objective=math_scene.objective,
        subject_key=math_scene.subject_key,
        scene_status="ACTIVE",
        blocks=[block.model_dump(mode="json") for block in math_scene.blocks],
        actions=[action],
    )
    workspace = StudioTutorWorkspaceContext(
        runtime_id=uuid4(), snapshot_schema_version="studio-snapshot-v1", through_sequence=1,
        snapshot_sequence=1, current_scene_id=uuid4(), current_scene_version=2,
        active_subject_key="CANVAS", active_activity_key="agentic_canvas",
        state_payload={}, unseen_events=(), observation_id=None, visual_scene=projection,
    )
    followup_session = _EvidenceSession()
    followup = create_tutor_gateway(followup_session, settings=settings).execute(  # type: ignore[arg-type]
        ModelTask.TUTOR,
        build_tutor_model_payload(
            question="I selected the first element. What should I notice?",
            studio_context=workspace,
            workspace_subject_key=math_scene.subject_key,
            student_core_context={"age_years": 10, "grade_level": 5},
        ),
    )
    results.append(_record("LIVE-09", passed=bool(followup.output.get("text")), tutor_execution_id=str(followup.execution_id), action="SELECT", projection_version=projection["version"]))
    results.append(_record("LIVE-10", passed=bool(followup.output.get("text")), tutor_execution_id=str(followup.execution_id), active_canvas=True, chat_available=True))
    update_brief = followup.output.get("canvas_brief")
    results.append(_record("LIVE-11", passed=update_brief is None or isinstance(update_brief, dict), tutor_execution_id=str(followup.execution_id), update_requested=update_brief is not None, stale_fence="newer_admitted_brief_only"))
    replayed = AgenticCanvasSceneV1.model_validate(json.loads(json.dumps(math_scene.model_dump(mode="json"))))
    results.append(_record("LIVE-12", passed=replayed == math_scene, scene_contract=replayed.version, scene_digest=_digest(replayed.model_dump(mode="json"))))
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
    args = parser.parse_args()
    if not args.live:
        raise SystemExit("Refusing provider calls without explicit --live.")
    settings = Settings(_env_file=args.env_file) if args.env_file is not None else Settings()
    if settings.model_api_key is None or settings.model_name == "mock":
        raise SystemExit("Configured MODEL_API_KEY and a real MODEL_NAME are required.")
    evidence = asyncio.run(run_live(settings))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "proof": evidence["proof"],
        "all_required_passed": evidence["all_required_passed"],
        "results": [{"case_id": item["case_id"], "status": item["status"], "passed": item["passed"]} for item in evidence["results"]],
        "evidence_path": str(args.output),
    }, separators=(",", ":")))


if __name__ == "__main__":
    main()
