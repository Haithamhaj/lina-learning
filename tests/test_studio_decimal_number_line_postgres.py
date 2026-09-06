"""Number-line production activation and durable state; isolated PostgreSQL only."""
import os
from copy import deepcopy

import pytest
from sqlalchemy import select

from test_studio_make_ten_postgres import postgres_session_factory, _student, _learning_session, _tutor_source
from services.studio.subjects import decimal_number_line as math
from services.studio.subjects import production_subject_registry, PRODUCTION_CURRENT_PROFILE_VERSIONS
from services.studio.router import WorkspaceAuthorityContext, route_workspace_intent
from services.studio.workspace_intent import WorkspaceIntent
from services.studio.activity_activation import activate_known_workspace_activity
from services.studio.service import StudioStateService, StaleSceneVersion
from services.studio.contracts import AppendStudioEventCommand, StudioActor
from services.platform.db.models import StudioSnapshot, StudioStudentInteraction

pytestmark = pytest.mark.skipif(not os.getenv('DATABASE_URL'), reason='Isolated PostgreSQL required')


def audit(ref):
    intent = WorkspaceIntent.model_validate(dict(version='workspace-intent-v1', action='OPEN_ACTIVITY', subject_key='MATH', activity_hint=math.ACTIVITY_KEY,
        concept_keys=[], learning_goal=None, representation_need='INTERACTIVE', expected_student_response_mode='WORKSPACE', presentation_sequence='PARALLEL', source_references=[ref], safe_text_fallback=None))
    decision = route_workspace_intent(intent, WorkspaceAuthorityContext(registry=production_subject_registry(), current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS, authorized_source_references=(ref,)))
    return dict(intent_status='VALID', intent=intent.model_dump(mode='json'), decision=decision.as_audit_payload())


@pytest.mark.parametrize('problem', math.PROBLEMS, ids=lambda p:p.key)
def test_authored_activation_operations_rebuild_and_replacement(postgres_session_factory, problem):
    with postgres_session_factory.begin() as session:
        student = _student(session, 'decimal-test')
        learning = _learning_session(session, student)
        segment, message = _tutor_source(session, learning)
        source_audit = audit(problem.source_ref)
        message.payload = {'workspace': source_audit}
        session.flush()
        def activate():
            return activate_known_workspace_activity(session, learning_session=learning, source_tutor_message=message, source_segment_id=segment.id, workspace_audit=source_audit)
        scene = activate()
        assert scene is not None
        assert scene.seed_payload == math.scene_seed(problem.source_ref)
        service = StudioStateService(session)
        def snapshot():
            return session.execute(select(StudioSnapshot).where(StudioSnapshot.studio_runtime_id==scene.studio_runtime_id)).scalar_one()
        def command(key, payload, nonce):
            return AppendStudioEventCommand(runtime_id=scene.studio_runtime_id, student_id=student.id, learning_session_id=learning.id,
                actor=StudioActor.STUDENT, event_kind=None, event_schema_version=None, scene_id=scene.id, base_scene_version=scene.scene_version,
                action_key=key, payload_schema_version=math.payload_version(key), payload=payload, idempotency_key=nonce)
        first = scene.seed_payload['points'][0]
        move = command('PLACE_POINT', dict(point_id=first['id'],from_value=None,value=scene.seed_payload['axis_min']), 'move-1')
        event = service.append_event(move)
        assert service.append_event(move).event.id == event.event.id
        before = deepcopy(snapshot().state_payload)
        assert activate().id == scene.id
        assert snapshot().state_payload == before
        stale = command('PLACE_POINT', dict(point_id=first['id'],from_value=None,value=first['value']), 'stale')
        from dataclasses import replace
        with pytest.raises(StaleSceneVersion):
            service.append_event(replace(stale, base_scene_version=0))
        assert snapshot().state_payload == before
        assert session.execute(select(StudioStudentInteraction)).scalars().all() == []
        for point in scene.seed_payload['points']:
            state = snapshot().state_payload.get(math.ACTIVITY_KEY, scene.seed_payload)
            service.append_event(command('PLACE_POINT', dict(point_id=point['id'], from_value=state['positions'][point['id']], value=point['value']), 'place-'+point['id']))
        choice = 'EQ' if problem.mode=='COMPARE' else scene.seed_payload['endpoints'][0]
        service.append_event(command('SELECT_ANSWER', dict(from_selection=None,selection=choice), 'select'))
        attempt = snapshot().state_payload[math.ACTIVITY_KEY]
        service.append_event(command('SUBMIT_CONFIGURATION', dict(source_ref=problem.source_ref, positions=attempt['positions'], selection=choice), 'submit'))
        assert len(session.execute(select(StudioStudentInteraction)).scalars().all()) == 1
        assert service.rebuild_snapshot(runtime_id=scene.studio_runtime_id, student_id=student.id)['state_payload'] == snapshot().state_payload


@pytest.mark.parametrize('ref', ['decimal-line:v1:compare-less','decimal-line:v1:round-midpoint'])
def test_api_real_mock_factory_original_submission_and_later_snapshot(postgres_session_factory, monkeypatch, ref):
    from uuid import UUID
    from test_studio_make_ten_postgres import _client, _clear_overrides
    from services.platform.db.models import LearningMessage, AIExecution, StudioScene
    from services.tutor.runtime import LocalTutorProvider
    observed=[]
    original=LocalTutorProvider.execute
    def observe(self, route, payload):
        observed.append(deepcopy(payload))
        return original(self,route,payload)
    monkeypatch.setattr(LocalTutorProvider,'execute',observe)
    with postgres_session_factory.begin() as session:
        student=_student(session,'decimal-api')
        learning=_learning_session(session,student)
        segment,message=_tutor_source(session,learning)
        source_audit=audit(ref);message.payload={'workspace':source_audit};session.flush()
        scene=activate_known_workspace_activity(session,learning_session=learning,source_tutor_message=message,source_segment_id=segment.id,workspace_audit=source_audit)
        runtime_id,scene_id,version=scene.studio_runtime_id,scene.id,scene.scene_version
        seed=deepcopy(scene.seed_payload)
        student_id,session_id=student.id,learning.id
    client=_client(postgres_session_factory,subject='decimal-api')
    def operation(key,payload,nonce, expected=200):
        nonlocal version
        response=client.post(f'/api/v1/student/studio/{runtime_id}/operations',json=dict(scene_id=str(scene_id),base_scene_version=version,action_key=key,payload=payload,idempotency_key=nonce))
        assert response.status_code==expected,response.text
        if expected==200:
            with postgres_session_factory.begin() as session:
                version=session.get(StudioScene,scene_id).scene_version
        return response
    try:
        before=client.get(f'/api/v1/student/studio/{runtime_id}/snapshot').json()
        operation('PLACE_POINT',dict(point_id='unknown',from_value=None,value=seed['axis_min']),'unknown',422)
        operation('PLACE_POINT',dict(point_id=seed['points'][0]['id'],from_value=None,value=seed['axis_min']-1),'outside',422)
        operation('PLACE_POINT',dict(point_id=seed['points'][0]['id'],from_value=seed['axis_min'],value=seed['axis_min']),'mismatch',422)
        operation('SUBMIT_CONFIGURATION',dict(source_ref=ref,positions=seed['positions'],selection=None),'incomplete',422)
        with postgres_session_factory.begin() as session:
            _student(session,'decimal-other')
        other=_client(postgres_session_factory,subject='decimal-other')
        assert other.get(f'/api/v1/student/studio/{runtime_id}/snapshot').status_code==404
        assert other.post(f'/api/v1/student/studio/{runtime_id}/operations',json=dict(scene_id=str(scene_id),base_scene_version=version,action_key='PLACE_POINT',payload=dict(point_id=seed['points'][0]['id'],from_value=None,value=seed['axis_min']),idempotency_key='cross-student')).status_code==404
        client=_client(postgres_session_factory,subject='decimal-api')
        assert client.get(f'/api/v1/student/studio/{runtime_id}/snapshot').json()==before
        # Legitimately wrong placement and answer reach the server, not a React answer gate.
        positions={p['id']:seed['axis_min'] for p in seed['points']}
        for point in seed['points']:
            assert operation('PLACE_POINT',dict(point_id=point['id'],from_value=None,value=positions[point['id']]),'wrong-'+point['id']).json()['student_interaction_id'] is None
        choice='GT' if seed['mode']=='COMPARE' else seed['endpoints'][0]
        operation('SELECT_ANSWER',dict(from_selection=None,selection=choice),'choice')
        assert observed==[]
        submitted=dict(source_ref=ref,positions=positions.copy(),selection=choice)
        result=operation('SUBMIT_CONFIGURATION',submitted,'submit')
        interaction=result.json()['student_interaction_id']
        point=seed['points'][0]
        operation('PLACE_POINT',dict(point_id=point['id'],from_value=positions[point['id']],value=point['value']),'later')
        response=client.post(f'/api/v1/student/studio/{runtime_id}/interactions/{interaction}/turn/stream')
        assert response.status_code==200,response.text
        assert len(observed)==1
        source=observed[0]['studio_interaction_context']['source']
        assert source['event']['action_payload']==submitted
        assert source['event']['validation']['status']=='INVALID'
        assert source['live_subject']['broad_subject']=='MATH'
        assert source['live_subject']['origin']=='CANVAS_SCENE'
        current=observed[0]['studio_interaction_context']['workspace']['state'][math.ACTIVITY_KEY]
        assert current['positions'][point['id']]==point['value']
        assert current['last_submission']==submitted
        with postgres_session_factory.begin() as session:
            item=session.get(StudioStudentInteraction,UUID(interaction))
            assert item.status=='COMPLETED'
            message=session.get(LearningMessage,item.tutor_message_id)
            assert message.role=='tutor' and message.session_id==session_id
            assert len(session.execute(select(AIExecution)).scalars().all())==1
            assert session.execute(select(LearningMessage).where(LearningMessage.role=='student')).scalars().all()==[]
            assert message.payload['turn_origin']=='STUDIO_INTERACTION'
        from services.studio.feed import StudioEventFeed
        _,_,feed_snapshot=StudioEventFeed(session_factory=postgres_session_factory)._snapshot_and_events(student_id=student_id,runtime_id=runtime_id,after_sequence=0)
        assert feed_snapshot==client.get(f'/api/v1/student/studio/{runtime_id}/snapshot').json()
    finally:
        _clear_overrides()


@pytest.mark.parametrize('ref',['decimal-line:v1:compare-equal','decimal-line:v1:round-carry'])
def test_normal_tutor_configured_mock_wiring_issues_and_activates_exact_reference(postgres_session_factory,monkeypatch,ref):
    from services.tutor.runtime import LocalTutorProvider
    from services.model_gateway.gateway import ModelResult
    from services.platform.db.models import StudioScene,LearningMessage
    from test_studio_make_ten_postgres import _make_ten_scene_command,_activate,_client,_clear_overrides
    calls=[]
    original=LocalTutorProvider.execute
    def authored_response(self,route,payload):
        assert ref in payload['input']
        assert all(s['ref']!=ref for s in payload['sources'])
        calls.append(payload)
        result=original(self,route,payload)
        return ModelResult(output={**result.output,'workspace_intent':audit(ref)['intent']})
    monkeypatch.setattr(LocalTutorProvider,'execute',authored_response)
    with postgres_session_factory.begin() as session:
        student=_student(session,'decimal-normal')
        learning=_learning_session(session,student)
        state=StudioStateService(session)
        runtime=state.get_or_create_runtime(student_id=student.id,learning_session_id=learning.id)
        historical=state.accept_scene(_make_ten_scene_command(student,learning))
        _activate(state,runtime_id=runtime.id,student=student,learning_session=learning,scene=historical)
        learning_id=learning.id
    client=_client(postgres_session_factory,subject='decimal-normal')
    try:
        response=client.post(f'/api/v1/student/daily/session/{learning_id}/turn/stream',json={'content':'Use the prepared decimal exercise.'})
        assert response.status_code==200,response.text
    finally:
        _clear_overrides()
    with postgres_session_factory.begin() as session:
        scene=session.execute(select(StudioScene).where(StudioScene.learning_session_id==learning_id,StudioScene.activity_key==math.ACTIVITY_KEY)).scalar_one()
        assert scene.seed_payload['source_ref']==ref
        source=session.get(LearningMessage,scene.source_message_id)
        assert source.payload['workspace']['decision']['target_source_reference']==ref
        assert source.role=='tutor' and len(calls)==1
