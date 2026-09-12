"""Publish one reviewed source-only correction without rewriting accepted history."""
from __future__ import annotations

from copy import deepcopy
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.platform.db.models import StudioCanvasSpecialistRun, StudioRuntime, StudioScene, StudioSnapshot, VisualArtifact, VisualArtifactBuild, VisualArtifactVersion, VisualArtifactInstance
from services.platform.storage import ObjectStorage
from services.studio.agentic_canvas import AGENTIC_CANVAS_SCENE_ADAPTER
from services.studio.contracts import AppendStudioEventCommand, CreateSceneCommand, StudioActor
from services.studio.custom_visual_builds import CustomVisualBuildResolver, repair_custom_visual_source
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.service import StudioStateService


def publish_custom_visual_source_refinement(session: Session, *, storage: ObjectStorage,
    scene_id: UUID, student_id: UUID, block_id: str, source: str, review_reason: str) -> StudioScene:
    """A trusted review operation; canonical educational semantics remain identical.

    The caller owns visual acceptance. This is never a sandbox-accessible route.
    Original Build, Scene, events and provider proposal remain untouched. The
    new Scene uses the same Tutor source authority and an immutable child Build.
    """
    if not review_reason.strip():
        raise ValueError("Source refinement requires concrete review evidence.")
    original = session.get(StudioScene, scene_id)
    if original is None or original.student_id != student_id:
        raise ValueError("Refinement Scene ownership is invalid.")
    session.scalar(select(StudioRuntime).where(StudioRuntime.id == original.studio_runtime_id).with_for_update())
    session.refresh(original)
    snapshot = session.scalar(select(StudioSnapshot).where(StudioSnapshot.studio_runtime_id == original.studio_runtime_id))
    if original.status != "ACTIVE" or snapshot is None or snapshot.current_scene_id != original.id:
        raise ValueError("Only the current active Scene can be refined.")
    seed = deepcopy(snapshot.state_payload.get("agentic_canvas", original.seed_payload))
    block = next((item for item in seed["blocks"] if item["block_id"] == block_id), None)
    if block is None or block["type"] != "CUSTOM_VISUAL":
        raise ValueError("Refinement requires an existing custom block.")
    parent_id = UUID(block["custom_visual_build_id"])
    parent_row = session.get(VisualArtifactBuild, parent_id)
    if parent_row is None:
        raise ValueError("Source refinement requires an existing parent Build.")
    run = session.get(StudioCanvasSpecialistRun, UUID(parent_row.technical_metadata["source_run_id"]))
    if run is None or run.student_id != student_id or run.studio_runtime_id != original.studio_runtime_id:
        raise ValueError("Source refinement must preserve its original run ownership.")
    parent = CustomVisualBuildResolver(storage).resolve(session, build_id=parent_id,
        student_id=student_id, runtime_id=original.studio_runtime_id)
    if source == parent.package.source:
        raise ValueError("Source refinement must correct the implementation.")
    child = repair_custom_visual_source(session, storage=storage, run=run, parent=parent, repaired_source=source)
    child.technical_metadata = {**child.technical_metadata, "parent_scene_id": str(original.id), "review_reason": review_reason, "repair_kind": "SOURCE_ONLY_REFINEMENT"}
    # A reviewed correction of a registered implementation gets its own Version;
    # never silently redirect a previously published immutable Version.
    if parent_row.artifact_version_id is not None:
        version = session.get(VisualArtifactVersion, parent_row.artifact_version_id)
        session.scalar(select(VisualArtifact).where(VisualArtifact.id == version.artifact_id).with_for_update())
        number = session.scalar(select(func.max(VisualArtifactVersion.version_number)).where(
            VisualArtifactVersion.artifact_id == version.artifact_id)) + 1
        revised = VisualArtifactVersion(
            artifact_id=version.artifact_id, parent_version_id=version.id,
            implementation_build_id=child.id, version_number=number, source_digest=child.source_digest,
            runtime_contract_version=version.runtime_contract_version, parameter_schema=deepcopy(version.parameter_schema),
            manifest_contract=deepcopy(version.manifest_contract), dependency_capabilities=list(version.dependency_capabilities),
            definition_payload=deepcopy(version.definition_payload), validation_status="VALIDATED",
            technical_evidence={"route": "SOURCE_ONLY_REFINEMENT", "parent_version_id": str(version.id),
                "implementation_build_id": str(child.id), "review_reason": review_reason, "manifest_digest": child.manifest_digest})
        session.add(revised)
        session.flush()
        child.artifact_version_id = revised.id
    block.update(custom_visual_build_id=str(child.id), manifest_digest=child.manifest_digest,
                 artifact_instance_id=f"refinement-{uuid4().hex}", bridge_nonce=uuid4().hex)
    seed = AGENTIC_CANVAS_SCENE_ADAPTER.validate_python(seed).model_dump(mode="json")
    state = StudioStateService(session)
    attributes = {name: getattr(original, name) for name in (
        "subject_key", "subject_profile_version", "activity_key", "artifact_type", "renderer_key", "renderer_version",
        "activity_contract_version", "payload_schema_version", "accessibility_payload", "locale", "direction",
        "source_message_id", "source_segment_id")}
    scene = state.accept_scene(CreateSceneCommand(student_id=student_id, learning_session_id=original.learning_session_id,
        concept_keys=tuple(original.concept_keys), source_asset_refs=tuple(original.source_asset_refs), seed_payload=seed, **attributes))
    if child.artifact_version_id is not None:
        session.add(VisualArtifactInstance(artifact_version_id=child.artifact_version_id,
            studio_scene_id=scene.id, student_id=student_id, bound_parameters=deepcopy(block["parameters"]),
            semantic_manifest=deepcopy(child.manifest_metadata),
            current_semantic_state={item["id"]: item["current_value"] for item in block["elements"]},
            locale=scene.locale, direction=scene.direction))
    for target, event, schema, payload in (
        (original, "studio.scene.status_changed", "studio-scene-status-v1", {"status": "SUPERSEDED"}),
        (scene, "studio.scene.activated", "studio-scene-activated-v1", {}),
    ):
        state.append_event(AppendStudioEventCommand(runtime_id=original.studio_runtime_id, student_id=student_id,
            learning_session_id=original.learning_session_id, event_kind=event, event_schema_version=CORE_EVENT_SCHEMA_VERSION,
            actor=StudioActor.SYSTEM, payload_schema_version=schema, payload=payload, scene_id=target.id,
            base_scene_version=target.scene_version, source_message_id=original.source_message_id,
            source_segment_id=original.source_segment_id, idempotency_key=f"source-refinement:{child.id}:{event}"))
    run.agent_execution_metadata = {**(run.agent_execution_metadata or {}), "source_refinement": {
        "parent_scene_id": str(original.id), "scene_id": str(scene.id), "parent_build_id": str(parent_id),
        "build_id": str(child.id), "manifest_digest": child.manifest_digest, "review_reason": review_reason}}
    return scene
