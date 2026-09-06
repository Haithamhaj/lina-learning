"""Real service/API/Gateway proof using guarded disposable PostgreSQL."""
import os
from copy import deepcopy
import pytest
from sqlalchemy import select
from test_studio_make_ten_postgres import postgres_session_factory,_student,_learning_session,_tutor_source
from services.studio.subjects import decimal_place_value as m,production_subject_registry,PRODUCTION_CURRENT_PROFILE_VERSIONS
from services.studio.workspace_intent import WorkspaceIntent
from services.studio.router import WorkspaceAuthorityContext,route_workspace_intent
from services.studio.activity_activation import activate_known_workspace_activity
from services.studio.service import StudioStateService
from services.studio.contracts import AppendStudioEventCommand,StudioActor
from services.platform.db.models import StudioSnapshot,StudioStudentInteraction

pytestmark=pytest.mark.skipif(not os.getenv('DATABASE_URL'),reason='Guarded disposable PostgreSQL required')


def audit(ref):
    intent=WorkspaceIntent.model_validate(dict(version='workspace-intent-v1',action='OPEN_ACTIVITY',subject_key='MATH',activity_hint=m.ACTIVITY_KEY,concept_keys=[],learning_goal=None,representation_need='INTERACTIVE',expected_student_response_mode='WORKSPACE',presentation_sequence='PARALLEL',source_references=[ref],safe_text_fallback=None))
    decision=route_workspace_intent(intent,WorkspaceAuthorityContext(registry=production_subject_registry(),current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS,authorized_source_references=(ref,)))
    return dict(intent_status='VALID',intent=intent.model_dump(mode='json'),decision=decision.as_audit_payload())


@pytest.mark.parametrize('problem',m.PROBLEMS,ids=lambda p:p.key)
def test_activation_submission_and_rebuild(postgres_session_factory,problem):
    with postgres_session_factory.begin() as session:
        student=_student(session,'place-value');learning=_learning_session(session,student)
        segment,message=_tutor_source(session,learning);source_audit=audit(problem.source_ref)
        message.payload={'workspace':source_audit};session.flush()
        def activate():
            return activate_known_workspace_activity(session,learning_session=learning,source_tutor_message=message,source_segment_id=segment.id,workspace_audit=source_audit)
        scene=activate();assert scene is not None
        service=StudioStateService(session)
        def command(key,payload,nonce):
            return AppendStudioEventCommand(runtime_id=scene.studio_runtime_id,student_id=student.id,learning_session_id=learning.id,actor=StudioActor.STUDENT,event_kind=None,event_schema_version=None,scene_id=scene.id,base_scene_version=scene.scene_version,action_key=key,payload_schema_version=m.payload_version(key),payload=payload,idempotency_key=nonce)
        edit=command('SET_RESULT',{'from_result':None,'result':0},'result')
        first=service.append_event(edit)
        assert service.append_event(edit).event.id==first.event.id
        assert session.scalars(select(StudioStudentInteraction)).all()==[]
        snapshot=session.scalar(select(StudioSnapshot).where(StudioSnapshot.studio_runtime_id==scene.studio_runtime_id))
        before=deepcopy(snapshot.state_payload)
        assert activate().id==scene.id and snapshot.state_payload==before
        service.append_event(command('SUBMIT_CONFIGURATION',dict(source_ref=problem.source_ref,pools=scene.seed_payload['pools'],result=0),'submit'))
        assert len(session.scalars(select(StudioStudentInteraction)).all())==1
        assert service.rebuild_snapshot(runtime_id=scene.studio_runtime_id,student_id=student.id)['state_payload']==snapshot.state_payload


@pytest.mark.parametrize('ref,want',[('decimal-place:v1:add-carry',212),('decimal-place:v1:subtract-zero-chain',125)])
def test_api_transitions_real_mock_gateway_and_original_source(postgres_session_factory,monkeypatch,ref,want):
    from uuid import UUID
    from test_studio_make_ten_postgres import _client,_clear_overrides
    from services.platform.db.models import StudioScene,LearningMessage,AIExecution,StudioEvent
    from services.tutor.runtime import LocalTutorProvider
    captured=[];original=LocalTutorProvider.execute
    def observe(self,route,payload):
        captured.append(deepcopy(payload));return original(self,route,payload)
    monkeypatch.setattr(LocalTutorProvider,'execute',observe)
    with postgres_session_factory.begin() as session:
        student=_student(session,'place-api');learning=_learning_session(session,student)
        segment,message=_tutor_source(session,learning);source_audit=audit(ref);message.payload={'workspace':source_audit};session.flush()
        scene=activate_known_workspace_activity(session,learning_session=learning,source_tutor_message=message,source_segment_id=segment.id,workspace_audit=source_audit)
        runtime_id,scene_id,version,student_id=scene.studio_runtime_id,scene.id,scene.scene_version,student.id
        seed=deepcopy(scene.seed_payload)
    client=_client(postgres_session_factory,subject='place-api');attempt=m.initial_attempt(seed);nonce=0
    def operation(key,payload,expected=200,base=None):
        nonlocal version,nonce,attempt
        nonce+=1
        body=dict(scene_id=str(scene_id),base_scene_version=version if base is None else base,action_key=key,payload=payload,idempotency_key=f'op-{nonce}')
        response=client.post(f'/api/v1/student/studio/{runtime_id}/operations',json=body)
        assert response.status_code==expected,response.text
        if expected==200:
            replay=client.post(f'/api/v1/student/studio/{runtime_id}/operations',json=body)
            assert replay.status_code==200 and replay.json()['event_id']==response.json()['event_id']
            snap=client.get(f'/api/v1/student/studio/{runtime_id}/snapshot').json()
            version=snap['active_scene_contract']['scene_version'];attempt=snap['state_payload'][m.ACTIVITY_KEY]
        return response
    try:
        before=client.get(f'/api/v1/student/studio/{runtime_id}/snapshot').json()
        operation('EXCHANGE',dict(from_pools=attempt['pools'],pool='unknown',place='ones',direction='DOWN'),422)
        operation('SET_RESULT',dict(from_result=None,result=1.25),422)
        operation('SET_RESULT',dict(from_result=0,result=125),422)
        operation('SET_RESULT',dict(from_result=None,result=125),409,base=0)
        assert client.get(f'/api/v1/student/studio/{runtime_id}/snapshot').json()==before
        with postgres_session_factory.begin() as session:_student(session,'place-other')
        other=_client(postgres_session_factory,subject='place-other')
        assert other.get(f'/api/v1/student/studio/{runtime_id}/snapshot').status_code==404
        assert other.post(f'/api/v1/student/studio/{runtime_id}/operations',json=dict(scene_id=str(scene_id),base_scene_version=version,action_key='SET_RESULT',payload={'from_result':None,'result':0},idempotency_key='cross')).status_code==404
        client=_client(postgres_session_factory,subject='place-api')
        if seed['mode']=='ADD':
            for pool in ('a','b'):
                for place,count in list(attempt['pools'][pool].items()):
                    if count:assert operation('TRANSFER',dict(from_pools=attempt['pools'],source=pool,target='result',place=place,count=count)).json()['student_interaction_id'] is None
            for place in ('hundredths','tenths'):
                operation('EXCHANGE',dict(from_pools=attempt['pools'],pool='result',place=place,direction='UP'))
            assert attempt['pools']['result']==dict(hundreds=0,tens=0,ones=2,tenths=1,hundredths=2)
        else:
            for place in ('ones','tenths'):operation('EXCHANGE',dict(from_pools=attempt['pools'],pool='remaining',place=place,direction='DOWN'))
            for place,count in [('tenths',7),('hundredths',5)]:operation('TRANSFER',dict(from_pools=attempt['pools'],source='remaining',target='removed',place=place,count=count))
            assert attempt['pools']['remaining']==dict(hundreds=0,tens=0,ones=1,tenths=2,hundredths=5)
            operation('TRANSFER',dict(from_pools=attempt['pools'],source='remaining',target='removed',place='hundredths',count=1),422)
        assert captured==[]
        with postgres_session_factory.begin() as session:
            assert session.scalars(select(StudioStudentInteraction)).all()==[]
            assert session.scalars(select(AIExecution)).all()==[]
        operation('SET_RESULT',dict(from_result=None,result=0))
        submitted=dict(source_ref=ref,pools=deepcopy(attempt['pools']),result=0)
        response=operation('SUBMIT_CONFIGURATION',submitted);interaction=response.json()['student_interaction_id']
        operation('SET_RESULT',dict(from_result=0,result=want))
        response=client.post(f'/api/v1/student/studio/{runtime_id}/interactions/{interaction}/turn/stream')
        assert response.status_code==200,response.text
        assert len(captured)==1
        ctx=captured[0]['studio_interaction_context']
        assert ctx['source']['event']['action_payload']==submitted
        assert ctx['source']['event']['validation']['status']=='INVALID'
        assert ctx['workspace']['state'][m.ACTIVITY_KEY]['result']==want
        assert ctx['workspace']['state'][m.ACTIVITY_KEY]['last_submission']==submitted
        assert ctx['source']['live_subject']['origin']=='CANVAS_SCENE'
        with postgres_session_factory.begin() as session:
            interaction_row=session.get(StudioStudentInteraction,UUID(interaction))
            assert interaction_row.status=='COMPLETED'
            message=session.get(LearningMessage,interaction_row.tutor_message_id)
            assert message.payload['turn_origin']=='STUDIO_INTERACTION'
            assert len(session.scalars(select(AIExecution)).all())==1
            assert session.scalars(select(LearningMessage).where(LearningMessage.role=='student')).all()==[]
            snapshot=session.scalar(select(StudioSnapshot).where(StudioSnapshot.studio_runtime_id==runtime_id))
            assert StudioStateService(session).rebuild_snapshot(runtime_id=runtime_id,student_id=student_id)['state_payload']==snapshot.state_payload
            events=session.scalars(select(StudioEvent).where(StudioEvent.studio_runtime_id==runtime_id).order_by(StudioEvent.sequence)).all()
            assert events[-1].sequence==snapshot.latest_event_sequence
            assert session.get(StudioScene,scene_id).scene_version==snapshot.current_scene_version
        from services.studio.feed import StudioEventFeed
        _,_,feed=StudioEventFeed(session_factory=postgres_session_factory)._snapshot_and_events(student_id=student_id,runtime_id=runtime_id,after_sequence=0)
        assert feed==client.get(f'/api/v1/student/studio/{runtime_id}/snapshot').json()
    finally:_clear_overrides()
