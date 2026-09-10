"""Short, deterministic CS-05 settlement from a completed Specialist Run."""
from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import (
    LearningMessage,
    StudioCanvasSpecialistRun,
    StudioGeneratedAsset,
    StudioRuntime,
    StudioScene,
)
from services.studio.agent.admission import (
    AGENTIC_CANVAS_CAPABILITY_IDENTITY,
    AGENTIC_CANVAS_SCENE_SCHEMA_VERSION,
    _canonical_digest,
)
from services.studio.agentic_canvas import AGENTIC_CANVAS_SCENE_ADAPTER, AgenticCanvasScene
from services.studio.canvas_brief import CanvasBriefContractError, parse_canvas_brief
from services.studio.canvas_specialist import (
    frozen_pack_identity_is_valid,
    proposal_contract,
)
from services.studio.contracts import (
    AppendStudioEventCommand,
    CreateSceneCommand,
    StudioActor,
)
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.service import StudioStateService
from services.studio.subjects.process_production import (
    ACTIVITY_KEY,
    ACTIVITY_VERSION,
    PROFILE_VERSION,
    RENDERER_KEY,
    RENDERER_VERSION,
    SCENE_PAYLOAD_SCHEMA_VERSION,
    proposal_to_scene_seed,
)


class ProcessAcceptanceFailure(RuntimeError):
    pass


def agentic_scene_contract(
    scene: AgenticCanvasScene,
    brief_payload: Mapping[str, object],
) -> dict[str, object]:
    """Map semantic Agent output to the one registered Studio Scene identity."""

    brief = parse_canvas_brief(dict(brief_payload))
    if brief is None or scene.subject_key != brief.subject_key:
        raise ValueError("Agentic Canvas proposal does not match its Tutor brief subject.")
    is_v2 = scene.version == "agentic-canvas-scene-v2"
    return {
        "subject_key": "CANVAS",
        "subject_profile_version": "agentic-canvas-profile-v2" if is_v2 else "agentic-canvas-profile-v1",
        "concept_keys": tuple(
            f"agentic:{block.type.lower()}:{block.block_id}" for block in scene.blocks
        ),
        "activity_key": "agentic_canvas",
        "activity_contract_version": "agentic-canvas-activity-v1",
        "artifact_type": "agentic-canvas",
        "renderer_key": "agentic-canvas",
        "renderer_version": "agentic-canvas-renderer-v2" if is_v2 else "agentic-canvas-renderer-v1",
        "payload_schema_version": scene.version,
        "seed_payload": scene.model_dump(mode="json"),
        "accessibility_payload": {
            "contract": "agentic-canvas-accessibility-v1",
            "text_equivalents": [block.accessibility.text_equivalent for block in scene.blocks],
        },
        "locale": brief.locale,
        "direction": brief.direction,
    }


def accept_completed_canvas_run(session: Session, run_id, *, before_commit=None) -> StudioScene | None:
    """Accept one valid current Canvas completion without another model call."""
    with session.begin_nested():
        unguarded_run = session.get(StudioCanvasSpecialistRun, run_id)
        if unguarded_run is None:
            return None
        # Match admission's Runtime -> Run lock order to avoid a new admission
        # deadlocking a settling completion.
        session.execute(select(StudioRuntime).where(StudioRuntime.id == unguarded_run.studio_runtime_id).with_for_update()).scalar_one()
        run = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.id == run_id).with_for_update()).scalar_one()
        if run.scene_id is not None:
            return session.get(StudioScene, run.scene_id)
        # The generation deadline governs provider/proposal completion.  A
        # proposal already committed within that deadline remains settleable
        # after a worker crash or later reconciliation.
        completed_after_deadline = (
            run.deadline_at is not None
            and (run.completed_at is None or run.completed_at >= run.deadline_at)
        )
        if run.status != "COMPLETED" or not isinstance(run.proposal_payload, dict) or completed_after_deadline:
            if run.status == "COMPLETED":
                run.status, run.failure_metadata = "REJECTED", {"code": "STALE_OR_INCOMPLETE_ACCEPTANCE"}
            return None
        if run.capability_profile_version == AGENTIC_CANVAS_CAPABILITY_IDENTITY:
            return _accept_completed_agentic_run_locked(
                session,
                run,
                before_commit=before_commit,
            )
        message = session.execute(select(LearningMessage).where(LearningMessage.id == run.source_message_id, LearningMessage.session_id == run.learning_session_id, LearningMessage.role == "tutor")).scalar_one_or_none()
        visual = message.payload.get("workspace_visual") if message is not None and isinstance(message.payload, dict) else None
        pack = visual.get("frozen_composition_pack") if isinstance(visual, dict) else None
        if not isinstance(pack, dict) or visual.get("status") != "ADMITTED" or visual.get("order_digest") != run.order_digest or sha256(json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest() != run.order_digest:
            run.status, run.failure_metadata = "REJECTED", {"code": "CAUSAL_ORDER_STALE"}; return None
        try:
            proposal_contract(run.capability_profile_version, run.output_schema_version)
        except ValueError:
            run.status, run.failure_metadata = "REJECTED", {"code": "CAPABILITY_IDENTITY_INVALID"}; return None
        expected_subject = "PROCESS" if run.capability_profile_version.startswith("process-") else "MATH"
        if (run.subject_key != expected_subject or not isinstance(pack.get("capability_pack"), dict)
                or pack["capability_pack"].get("identity") != run.capability_profile_version
                or not frozen_pack_identity_is_valid(pack, run.capability_profile_version)):
            run.status, run.failure_metadata = "REJECTED", {"code": "CAPABILITY_IDENTITY_INVALID"}; return None
        admitted_messages = session.scalars(
            select(LearningMessage).where(LearningMessage.session_id == run.learning_session_id, LearningMessage.role == "tutor")
            .order_by(LearningMessage.created_at.desc(), LearningMessage.id.asc())
        )
        newest = next((candidate for candidate in admitted_messages if isinstance(candidate.payload, dict)
                       and isinstance(candidate.payload.get("workspace_visual"), dict)
                       and candidate.payload["workspace_visual"].get("status") == "ADMITTED"), None)
        if newest is None or newest.id != message.id:
            run.status, run.failure_metadata = "REJECTED", {"code": "SUPERSEDED_BY_NEWER_ADMITTED_ORDER"}; return None
        active = session.execute(select(StudioScene).where(StudioScene.studio_runtime_id == run.studio_runtime_id, StudioScene.status == "ACTIVE").with_for_update()).scalar_one_or_none()
        if active is not None and (active.id != run.base_scene_id or active.scene_version != run.base_scene_version):
            # A result composed against a different active version cannot be safely rebased.
            run.status, run.failure_metadata = "REJECTED", {"code": "ACTIVE_SCENE_CHANGED"}; return None
        if active is None and (run.base_scene_id is not None or run.base_scene_version != 0):
            run.status, run.failure_metadata = "REJECTED", {"code": "ACTIVE_SCENE_MISSING"}; return None
        locale = pack.get("locale")
        direction = pack.get("direction")
        if not isinstance(locale, str) or not isinstance(direction, str):
            run.status, run.failure_metadata = "REJECTED", {"code": "FROZEN_LOCALE_DIRECTION_INVALID"}; return None
        # This is the narrow application-owned conversion boundary for a
        # durable proposal.  Its validation failures are permanent proposal
        # rejection, unlike database/transaction failures later in settlement.
        try:
            if run.capability_profile_version.startswith("process-"):
                seed = proposal_to_scene_seed(
                    run.proposal_payload,
                    pack,
                    locale="ar" if locale.startswith("ar") else "en",
                    direction=direction,
                )
                scene_contract = {
                    "subject_key": "SCIENCE", "profile_version": PROFILE_VERSION,
                    "concept_keys": tuple(stage["id"] for stage in seed["stages"]),
                    "activity_key": ACTIVITY_KEY, "activity_version": ACTIVITY_VERSION,
                    "renderer_key": RENDERER_KEY, "renderer_version": RENDERER_VERSION,
                    "seed_version": SCENE_PAYLOAD_SCHEMA_VERSION, "artifact_type": "visual-explanation",
                    "accessibility": "process-visual-production-v1",
                }
            else:
                from services.studio.subjects.canvas_production import (
                    PROFILE_VERSION as CANVAS_PROFILE_VERSION,
                )
                from services.studio.subjects.canvas_production import (
                    contract_for_pattern,
                    proposal_to_scene_contract,
                )
                seed = proposal_to_scene_contract(
                    run.proposal_payload,
                    pack,
                    locale="ar" if locale.startswith("ar") else "en",
                    direction=direction,
                )
                bounded = contract_for_pattern(str(seed["pattern"]))
                if seed["pattern"] == "SPATIAL_MANIPULATION":
                    concept_keys = tuple(item["semantic_key"] for item in (*seed["objects"], *seed["targets"]))
                elif seed["pattern"] == "MATH_VISUALIZATION":
                    concept_keys = (seed["point"]["semantic_key"],)
                else:
                    concept_keys = ("math-expression",)
                scene_contract = {
                    "subject_key": "MATH", "profile_version": CANVAS_PROFILE_VERSION,
                    "concept_keys": concept_keys,
                    "activity_key": bounded["activity_key"], "activity_version": bounded["activity_version"],
                    "renderer_key": bounded["renderer_key"], "renderer_version": bounded["renderer_version"],
                    "seed_version": bounded["seed_version"], "artifact_type": "interactive-activity",
                    "accessibility": "canvas-production-v1",
                }
        except (ValidationError, ValueError):
            run.status, run.failure_metadata = "REJECTED", {"code": "PROPOSAL_TO_SCENE_INVALID"}
            return None
        state = StudioStateService(session)
        scene = state.accept_scene(CreateSceneCommand(student_id=run.student_id, learning_session_id=run.learning_session_id,
            subject_key=scene_contract["subject_key"], subject_profile_version=scene_contract["profile_version"], concept_keys=scene_contract["concept_keys"],
            activity_key=scene_contract["activity_key"], artifact_type=scene_contract["artifact_type"], renderer_key=scene_contract["renderer_key"], renderer_version=scene_contract["renderer_version"],
            activity_contract_version=scene_contract["activity_version"], payload_schema_version=scene_contract["seed_version"], seed_payload=seed,
            accessibility_payload={"contract": scene_contract["accessibility"]}, locale=locale, direction=direction,
            source_message_id=message.id, source_segment_id=message.segment_id))
        if active is not None:
            state.append_event(AppendStudioEventCommand(runtime_id=run.studio_runtime_id, student_id=run.student_id, learning_session_id=run.learning_session_id,
                event_kind="studio.scene.status_changed", event_schema_version=CORE_EVENT_SCHEMA_VERSION, actor=StudioActor.SYSTEM,
                payload_schema_version="studio-scene-status-v1", payload={"status": "SUPERSEDED"}, scene_id=active.id,
                base_scene_version=active.scene_version, source_message_id=message.id, source_segment_id=message.segment_id,
                idempotency_key=f"canvas-production-supersede:{run.id}"))
        state.append_event(AppendStudioEventCommand(runtime_id=run.studio_runtime_id, student_id=run.student_id, learning_session_id=run.learning_session_id,
            event_kind="studio.scene.activated", event_schema_version=CORE_EVENT_SCHEMA_VERSION, actor=StudioActor.SYSTEM,
            payload_schema_version="studio-scene-activated-v1", payload={}, scene_id=scene.id, base_scene_version=scene.scene_version,
            source_message_id=message.id, source_segment_id=message.segment_id, idempotency_key=f"canvas-production-activate:{run.id}"))
        run.scene_id, run.accepted_scene_version = scene.id, scene.scene_version
        if before_commit is not None:
            before_commit()
        return scene


def _accept_completed_agentic_run_locked(
    session: Session,
    run: StudioCanvasSpecialistRun,
    *,
    before_commit=None,
) -> StudioScene | None:
    """Settle a validated Agentic proposal through existing Studio state."""

    if run.output_schema_version != AGENTIC_CANVAS_SCENE_SCHEMA_VERSION:
        run.status, run.failure_metadata = "REJECTED", {"code": "CAPABILITY_IDENTITY_INVALID"}
        return None
    message = session.execute(
        select(LearningMessage).where(
            LearningMessage.id == run.source_message_id,
            LearningMessage.session_id == run.learning_session_id,
            LearningMessage.role == "tutor",
        )
    ).scalar_one_or_none()
    audit = (
        message.payload.get("agentic_canvas")
        if message is not None and isinstance(message.payload, dict)
        else None
    )
    try:
        brief = (
            parse_canvas_brief(audit.get("brief"))
            if isinstance(audit, dict) and audit.get("status") == "ADMITTED"
            else None
        )
    except CanvasBriefContractError:
        brief = None
    if (
        brief is None
        or audit.get("brief_digest") != run.order_digest
        or _canonical_digest(brief.model_dump(mode="json")) != run.order_digest
        or brief.subject_key != run.subject_key
    ):
        run.status, run.failure_metadata = "REJECTED", {"code": "CANVAS_BRIEF_LINEAGE_INVALID"}
        return None

    # Only a newer admitted Canvas brief supersedes this result. Ordinary Chat
    # turns remain usable while the bounded composition is running.
    admitted_messages = session.scalars(
        select(LearningMessage)
        .where(
            LearningMessage.session_id == run.learning_session_id,
            LearningMessage.role == "tutor",
        )
        .order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())
    )
    newest_admitted = next(
        (
            candidate
            for candidate in admitted_messages
            if isinstance(candidate.payload, dict)
            and isinstance(candidate.payload.get("agentic_canvas"), dict)
            and candidate.payload["agentic_canvas"].get("status") == "ADMITTED"
        ),
        None,
    )
    if newest_admitted is None or newest_admitted.id != message.id:
        run.status, run.failure_metadata = "REJECTED", {"code": "SUPERSEDED_BY_NEWER_AGENTIC_CANVAS_BRIEF"}
        return None

    active = session.execute(
        select(StudioScene)
        .where(
            StudioScene.studio_runtime_id == run.studio_runtime_id,
            StudioScene.status == "ACTIVE",
        )
        .with_for_update()
    ).scalar_one_or_none()
    if active is not None and (
        active.id != run.base_scene_id or active.scene_version != run.base_scene_version
    ):
        run.status, run.failure_metadata = "REJECTED", {"code": "ACTIVE_SCENE_CHANGED"}
        return None
    if active is None and (run.base_scene_id is not None or run.base_scene_version != 0):
        run.status, run.failure_metadata = "REJECTED", {"code": "ACTIVE_SCENE_MISSING"}
        return None

    try:
        scene_payload = AGENTIC_CANVAS_SCENE_ADAPTER.validate_python(run.proposal_payload)
        if run.proposal_digest != _canonical_digest(scene_payload.model_dump(mode="json")):
            raise ValueError("Agentic Canvas proposal digest is invalid.")
        contract = agentic_scene_contract(scene_payload, brief.model_dump(mode="json"))
        _validate_generated_asset_lineage(session, run, scene_payload)
    except (ValidationError, ValueError):
        run.status, run.failure_metadata = "REJECTED", {"code": "PROPOSAL_TO_SCENE_INVALID"}
        return None

    state = StudioStateService(session)
    scene = state.accept_scene(
        CreateSceneCommand(
            student_id=run.student_id,
            learning_session_id=run.learning_session_id,
            subject_key=str(contract["subject_key"]),
            subject_profile_version=str(contract["subject_profile_version"]),
            concept_keys=contract["concept_keys"],
            activity_key=str(contract["activity_key"]),
            artifact_type=str(contract["artifact_type"]),
            renderer_key=str(contract["renderer_key"]),
            renderer_version=str(contract["renderer_version"]),
            activity_contract_version=str(contract["activity_contract_version"]),
            payload_schema_version=str(contract["payload_schema_version"]),
            seed_payload=contract["seed_payload"],
            accessibility_payload=contract["accessibility_payload"],
            locale=str(contract["locale"]),
            direction=str(contract["direction"]),
            source_message_id=message.id,
            source_segment_id=message.segment_id,
        )
    )
    if active is not None:
        state.append_event(
            AppendStudioEventCommand(
                runtime_id=run.studio_runtime_id,
                student_id=run.student_id,
                learning_session_id=run.learning_session_id,
                event_kind="studio.scene.status_changed",
                event_schema_version=CORE_EVENT_SCHEMA_VERSION,
                actor=StudioActor.SYSTEM,
                payload_schema_version="studio-scene-status-v1",
                payload={"status": "SUPERSEDED"},
                scene_id=active.id,
                base_scene_version=active.scene_version,
                source_message_id=message.id,
                source_segment_id=message.segment_id,
                idempotency_key=f"agentic-canvas-supersede:{run.id}",
            )
        )
    state.append_event(
        AppendStudioEventCommand(
            runtime_id=run.studio_runtime_id,
            student_id=run.student_id,
            learning_session_id=run.learning_session_id,
            event_kind="studio.scene.activated",
            event_schema_version=CORE_EVENT_SCHEMA_VERSION,
            actor=StudioActor.SYSTEM,
            payload_schema_version="studio-scene-activated-v1",
            payload={},
            scene_id=scene.id,
            base_scene_version=scene.scene_version,
            source_message_id=message.id,
            source_segment_id=message.segment_id,
            idempotency_key=f"agentic-canvas-activate:{run.id}",
        )
    )
    run.scene_id = scene.id
    run.accepted_scene_version = scene.scene_version
    run.failure_metadata = None
    if before_commit is not None:
        before_commit()
    return scene


def _validate_generated_asset_lineage(
    session: Session,
    run: StudioCanvasSpecialistRun,
    scene: AgenticCanvasScene,
) -> None:
    for block in scene.blocks:
        if block.type != "IMAGE":
            continue
        try:
            asset_id = UUID(block.studio_generated_asset_id)
        except ValueError as error:
            raise ValueError("Agentic Canvas generated asset identity is invalid.") from error
        asset = session.execute(
            select(StudioGeneratedAsset).where(
                StudioGeneratedAsset.id == asset_id,
                StudioGeneratedAsset.student_id == run.student_id,
                StudioGeneratedAsset.learning_session_id == run.learning_session_id,
                StudioGeneratedAsset.studio_runtime_id == run.studio_runtime_id,
                StudioGeneratedAsset.source_run_id == run.id,
            )
        ).scalar_one_or_none()
        if asset is None:
            raise ValueError("Agentic Canvas generated asset is outside its run lineage.")


def accept_completed_process_run(session: Session, run_id, *, before_commit=None) -> StudioScene | None:
    """Backward-compatible name retained for accepted Process callers."""
    return accept_completed_canvas_run(session, run_id, before_commit=before_commit)
