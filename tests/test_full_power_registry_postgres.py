"""Rollback-only registry tests; preserve existing disposable live evidence."""
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from test_agentic_canvas_lifecycle_postgres import _admitted_message
from test_full_power_canvas import _manifest
from services.platform.db import models as m
from services.platform.storage import LocalObjectStorage
from services.studio.agent.admission import admit_agentic_canvas_brief
from services.studio.custom_visual_builds import (
    CustomVisualBuildResolver, CustomVisualBuildResolutionError,
    persist_custom_visual_build, promote_custom_visual_build, adapt_promoted_custom_visual_build,
)
from services.studio.full_power_canvas import CustomVisualPackageV1
from workers.agentic_canvas_handlers import _reusable_visuals_for_agent

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="Disposable PostgreSQL required")


def test_promotion_reuse_adapt_preserve_immutable_source_and_owner(tmp_path):
    engine = create_engine(os.environ["DATABASE_URL"])
    storage = LocalObjectStorage(tmp_path)
    resolver = CustomVisualBuildResolver(storage)
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(connection)
        try:
            student, learning, message = _admitted_message(session)
            run = admit_agentic_canvas_brief(session, student_id=student.id,
                learning_session_id=learning.id, source_message_id=message.id)
            source = "window.mount=(root,params,bridge)=>{root.textContent=params.label;}"
            package = CustomVisualPackageV1.model_validate({"version": "custom-visual-package-v1",
                "runtime_kind": "custom-visual", "dependencies": ["native-svg-v1"],
                "source": source, "manifest": _manifest(),
                "parameter_schema": {"type": "object", "properties": {"label": {"type": "string"}}}})
            build = persist_custom_visual_build(session, storage=storage, run=run, package=package)
            session.flush()
            arguments = dict(resolver=resolver, build_id=build.id, student_id=student.id,
                runtime_id=run.studio_runtime_id, stable_slug=f"fractions-{uuid4().hex}",
                semantic_purpose="Compare fractions", parameter_schema=package.parameter_schema,
                promotion_reason="Verified visible generalizable fraction control")
            version = promote_custom_visual_build(session, **arguments)
            assert promote_custom_visual_build(session, **arguments).id == version.id
            assert version.implementation_build_id == build.id
            assert version.source_digest == build.source_digest
            assert "source" not in version.definition_payload
            assert str(version.id) in _reusable_visuals_for_agent(session, student_id=student.id)
            assert str(version.id) not in _reusable_visuals_for_agent(session, student_id=uuid4())
            with pytest.raises(CustomVisualBuildResolutionError):
                resolver.resolve_artifact_version(session, version_id=version.id, student_id=uuid4(), runtime_id=uuid4())
            assert resolver.resolve_artifact_version(session, version_id=version.id,
                student_id=student.id, runtime_id=uuid4()).package.source == source
            with pytest.raises(ValueError, match="not only instance parameters"):
                adapt_promoted_custom_visual_build(session, resolver=resolver, storage=storage,
                    parent_version_id=version.id, student_id=student.id, runtime_id=run.studio_runtime_id,
                    run=run, package=package, generalized_change="Only labels")
            changed = CustomVisualPackageV1.model_validate({**package.model_dump(mode="json"),
                "source": source + "\n// Generalized numeric display\n" + "window.formatFraction=x=>String(x);"})
            child = adapt_promoted_custom_visual_build(session, resolver=resolver, storage=storage,
                parent_version_id=version.id, student_id=student.id, runtime_id=run.studio_runtime_id,
                run=run, package=changed, generalized_change="Adds reusable fraction formatting capability")
            assert child.parent_version_id == version.id
            child_build = session.get(m.VisualArtifactBuild, child.implementation_build_id)
            assert child_build.technical_metadata["parent_build_id"] == str(build.id)
            assert child_build.id != build.id and child.source_digest != version.source_digest
            assert resolver.resolve(session, build_id=build.id, student_id=student.id,
                runtime_id=run.studio_runtime_id).package.source == source
        finally:
            session.close()
            transaction.rollback()
    engine.dispose()


@pytest.mark.parametrize("route", ["REUSE", "ADAPT"])
def test_reuse_settlement_in_new_runtime_resolves_real_build_and_replays(tmp_path, monkeypatch, route):
    import json
    from datetime import UTC, datetime
    from hashlib import sha256
    from services.studio.agent.tools import create_reused_custom_visual
    from services.studio.agentic_canvas import AgenticCanvasSceneV3
    from services.studio.process_production_acceptance import accept_completed_canvas_run
    from services.studio.contracts import AppendStudioEventCommand, StudioActor
    from services.studio.service import StudioStateService
    import services.studio.custom_visual_builds as builds
    storage = LocalObjectStorage(tmp_path)
    monkeypatch.setattr(builds, "create_object_storage", lambda: storage)
    resolver = CustomVisualBuildResolver(storage)
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(connection)
        try:
            student, learning, message = _admitted_message(session)
            run = admit_agentic_canvas_brief(session, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id)
            package = CustomVisualPackageV1.model_validate({"version": "custom-visual-package-v1", "runtime_kind": "custom-visual",
                "dependencies": ["native-svg-v1"], "source": "window.mount=(root,params,bridge)=>{root.textContent=params.label;}",
                "manifest": _manifest(), "parameter_schema": {"type": "object", "properties": {"label": {"type": "string"}}}})
            build = persist_custom_visual_build(session, storage=storage, run=run, package=package)
            session.flush()
            version = promote_custom_visual_build(session, resolver=resolver, build_id=build.id, student_id=student.id,
                runtime_id=run.studio_runtime_id, stable_slug=f"reuse-{uuid4().hex}", semantic_purpose="Reusable fractions",
                parameter_schema=package.parameter_schema, promotion_reason="Accepted visual")
            later = m.LearningSession(student_id=student.id, subject="MATH", status="OPEN")
            session.add(later); session.flush()
            runtime = StudioStateService(session).get_or_create_runtime(student_id=student.id, learning_session_id=later.id)
            _, _, message2 = _admitted_message(session, student=student, learning=later)
            reuse = admit_agentic_canvas_brief(session, student_id=student.id, learning_session_id=later.id, source_message_id=message2.id)
            with pytest.raises(CustomVisualBuildResolutionError):
                resolver.resolve(session, build_id=build.id, student_id=student.id, runtime_id=runtime.id)
            block = create_reused_custom_visual(block_id="reuse", meaning="Compare a new fraction", label="Fraction",
                artifact_instance_id="new-instance", bridge_nonce="new-instance-nonce", build_id=str(build.id),
                manifest_digest=build.manifest_digest, manifest=package.manifest.model_dump(mode="json"), parameters={"label": "3/4"})
            if route == "ADAPT":
                changed = CustomVisualPackageV1.model_validate({**package.model_dump(mode="json"),
                    "source": package.source + ";window.fractionLabel=(n,d)=>n+'/'+d;"})
                block = block.model_copy(update={"package": changed, "custom_visual_build_id": None, "manifest_digest": None})
            scene = AgenticCanvasSceneV3.model_validate({"version": "agentic-canvas-scene-v3", "objective": "Compare two decimals on a number line.",
                "subject_key": "MATH", "presentation": {"layout": "FOCUS", "palette": "COOL", "motion": "NONE",
                    "placements": [{"block_id": "reuse", "role": "PRIMARY", "order": 0, "span": "FULL"}], "reveal_order": []},
                "blocks": [block.model_dump(mode="json")]})
            reuse.status = "COMPLETED"; reuse.completed_at = datetime.now(UTC)
            reuse.proposal_payload = scene.model_dump(mode="json")
            reuse.proposal_digest = sha256(json.dumps(reuse.proposal_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
            reuse.agent_execution_metadata = {"reusable_selections": [{"version_id": str(version.id), "mode": "REUSE", "parameters": {"label": "3/4"}}]}
            if route == "ADAPT":
                reuse.agent_execution_metadata = {"reusable_selections": [{"version_id": str(version.id), "mode": "ADAPT",
                    "parameters": {"label": "3/4"}, "block_id": "reuse", "generalized_change": "Adds a generalized fraction formatter"}]}
            session.flush()
            accepted = accept_completed_canvas_run(session, reuse.id, storage=storage)
            assert accepted is not None, reuse.failure_metadata
            session.flush()
            accepted_build_id = UUID(accepted.seed_payload["blocks"][0]["custom_visual_build_id"])
            resolved = resolver.resolve(session, build_id=accepted_build_id, student_id=student.id, runtime_id=runtime.id)
            if route == "REUSE":
                assert resolved.build_id == build.id and resolved.package.source == package.source
            else:
                accepted_build = session.get(m.VisualArtifactBuild, accepted_build_id)
                child = session.get(m.VisualArtifactVersion, accepted_build.artifact_version_id)
                assert child.parent_version_id == version.id
                assert accepted_build.technical_metadata["parent_build_id"] == str(build.id)
                assert child.source_digest != version.source_digest
            result = StudioStateService(session).append_event(AppendStudioEventCommand(runtime_id=runtime.id,
                student_id=student.id, learning_session_id=later.id, event_kind=None, event_schema_version=None,
                actor=StudioActor.STUDENT, payload_schema_version="agentic-canvas-action-v1",
                payload={"version": "agentic-canvas-action-v1", "action": "MOVE", "block_id": "reuse", "element_id": "fraction-a", "from_value": None, "to_value": "3/4"},
                idempotency_key="reuse-move", action_key="MOVE", scene_id=accepted.id, base_scene_version=accepted.scene_version,
                subject_key="CANVAS", activity_key="agentic_canvas"))
            rebuilt = StudioStateService(session).rebuild_snapshot(runtime_id=runtime.id, student_id=student.id)
            assert rebuilt == StudioStateService(session).snapshot_projection(result.snapshot)
            if route == "ADAPT":
                from services.studio.custom_visual_refinement import publish_custom_visual_source_refinement
                original_seed = json.dumps(accepted.seed_payload, sort_keys=True)
                refined = publish_custom_visual_source_refinement(session, storage=storage, scene_id=accepted.id,
                    student_id=student.id, block_id="reuse", source=resolved.package.source + ";window.displayLabel=x=>String(x);",
                    review_reason="Reviewed display correction; original meaning unchanged")
                assert refined.id != accepted.id and accepted.status == "SUPERSEDED"
                assert json.dumps(accepted.seed_payload, sort_keys=True) == original_seed
                refined_block = refined.seed_payload["blocks"][0]
                assert refined_block["manifest_digest"] == accepted.seed_payload["blocks"][0]["manifest_digest"]
                assert refined_block["elements"][0]["current_value"] == "3/4"
                revised_build = session.get(m.VisualArtifactBuild, UUID(refined_block["custom_visual_build_id"]))
                revised_version = session.get(m.VisualArtifactVersion, revised_build.artifact_version_id)
                assert revised_version.parent_version_id == child.id
                assert revised_version.implementation_build_id == revised_build.id
                assert child.implementation_build_id != revised_build.id
                from sqlalchemy import select
                revised_instance = session.scalar(select(m.VisualArtifactInstance).where(m.VisualArtifactInstance.studio_scene_id == refined.id))
                assert revised_instance.artifact_version_id == revised_version.id
                assert revised_instance.current_semantic_state["fraction-a"] == "3/4"
                with pytest.raises(ValueError, match="must correct the implementation"):
                    publish_custom_visual_source_refinement(session, storage=storage, scene_id=refined.id,
                        student_id=student.id, block_id="reuse", source=resolved.package.source + ";window.displayLabel=x=>String(x);",
                        review_reason="No-op review must not create another Build")
            assert resolver.resolve(session, build_id=build.id, student_id=student.id, runtime_id=run.studio_runtime_id).package.source == package.source
        finally:
            session.close(); transaction.rollback()
    engine.dispose()
