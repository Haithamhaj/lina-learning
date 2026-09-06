"""Prepare/read one authorized technical session through production Studio services."""
import json
import sys
from pathlib import Path
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from services.platform.db.connection import get_engine
from services.platform.db import models as m
from services.studio.service import StudioStateService
from services.studio.arabic_sentence_ordering_activation import activate_arabic_sentence_ordering_from_workspace_decision
from services.studio.workspace_intent import WorkspaceIntent
from services.studio.router import route_workspace_intent, WorkspaceAuthorityContext
from services.studio.subjects import production_subject_registry, PRODUCTION_CURRENT_PROFILE_VERSIONS

sid = UUID(sys.argv[1])
with Session(get_engine()) as db:
    ls = db.get(m.LearningSession, sid)
    assert ls and ls.status == "OPEN"
    runtime = db.scalar(select(m.StudioRuntime).where(m.StudioRuntime.learning_session_id == sid))
    assert runtime is not None
    service = StudioStateService(db)
    if "--prepare" in sys.argv:
        source = db.scalar(select(m.LearningMessage).where(m.LearningMessage.session_id == sid, m.LearningMessage.role == "tutor").order_by(m.LearningMessage.created_at.desc()).limit(1))
        assert source and "Arabic technical acceptance" in source.content
        intent = WorkspaceIntent.model_validate(dict(version="workspace-intent-v1", action="OPEN_ACTIVITY", subject_key="ARABIC", concept_keys=["sentence-order"], learning_goal="Arrange the declared verb-initial sentence.", activity_hint="arabic_sentence_ordering_workspace", representation_need="INTERACTIVE", expected_student_response_mode="WORKSPACE", presentation_sequence="PARALLEL", source_references=[], safe_text_fallback="رتّب الكلمات."))
        decision = route_workspace_intent(intent, WorkspaceAuthorityContext(registry=production_subject_registry(), current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS))
        scene = activate_arabic_sentence_ordering_from_workspace_decision(db, learning_session=ls, source_tutor_message=source, source_segment_id=source.segment_id, workspace_audit={"intent_status":"VALID", "intent":intent.model_dump(mode="json"), "decision":decision.as_audit_payload()})
        assert scene is not None and scene.status == "ACTIVE"
        db.commit()
    events = list(db.scalars(select(m.StudioEvent).where(m.StudioEvent.studio_runtime_id == runtime.id).order_by(m.StudioEvent.sequence)))
    interactions = list(db.scalars(select(m.StudioStudentInteraction).where(m.StudioStudentInteraction.learning_session_id == sid)))
    messages = list(db.scalars(select(m.LearningMessage).where(m.LearningMessage.session_id == sid)))
    report={"session_id":str(sid),"runtime_id":str(runtime.id),"snapshot":service.runtime_state(runtime_id=runtime.id,student_id=ls.student_id),"events":[{"id":str(e.id),"sequence":e.sequence,"action":e.action_key,"payload":e.payload,"version":e.resulting_scene_version} for e in events],"interactions":[{"id":str(i.id),"status":i.status,"source_event_id":str(i.source_event_id),"execution":str(i.ai_execution_id),"tutor_message":str(i.tutor_message_id)} for i in interactions],"messages":[{"id":str(x.id),"role":x.role,"payload":x.payload} for x in messages],"execution_count":db.scalar(select(func.count()).select_from(m.AIExecution).where(m.AIExecution.learning_session_id==sid))}
    if "--save" in sys.argv:
        target=Path(__file__).parent / "durable-readback.json"
        target.write_text(json.dumps(report,default=str,ensure_ascii=False,indent=2)+"\n")
        print(json.dumps({"evidence":str(target),"events":len(events),"interactions":[i.status for i in interactions],"messages":[x.role for x in messages],"executions":report["execution_count"]}))
    else:
        print(json.dumps(report,default=str,ensure_ascii=False))
