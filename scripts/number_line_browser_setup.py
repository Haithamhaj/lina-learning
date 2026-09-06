"""Explicit prepared-scene setup in the existing authorized Daily test database.

Does not change credentials, accounts, roles, Parent links, schema or session expiry.
Reads the existing container configuration in memory; never prints credentials.
"""
import argparse
import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from uuid import UUID

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
TEST_STUDENT=UUID('7f080c93-7d2e-481a-89df-88cc495a8175')
DAILY_CONTAINER='lina-learning-daily-use-postgres'
DAILY_DATABASE='lina_daily_use'
WEB_ORIGIN='http://127.0.0.1:5002'
API_ORIGIN='http://127.0.0.1:8000'


def container_metadata():
    result=subprocess.run(['docker','inspect',DAILY_CONTAINER],capture_output=True,text=True,check=True)
    return json.loads(result.stdout)[0]


def database_url(container=None):
    from sqlalchemy.engine import URL
    data=container or container_metadata()
    values=dict(item.split('=',1) for item in data['Config']['Env'] if '=' in item)
    return URL.create('postgresql+psycopg',username=values['POSTGRES_USER'],password=values.get('POSTGRES_PASSWORD'),host='127.0.0.1',port=55435,database=values['POSTGRES_DB'])


def preflight_database_target(container, *, database_name, student_row, schema_version, expected_schema_version):
    name=str(container.get('Name','')).lstrip('/')
    configured=dict(item.split('=',1) for item in container.get('Config',{}).get('Env',()) if '=' in item).get('POSTGRES_DB')
    if name != DAILY_CONTAINER or configured != DAILY_DATABASE or database_name != DAILY_DATABASE:
        raise RuntimeError('Refusing browser writes: expected Daily-use database target is unavailable.')
    if not isinstance(student_row,Mapping) or student_row.get('id') != str(TEST_STUDENT) or not student_row.get('user_id'):
        raise RuntimeError('Refusing browser writes: expected existing authorized test Student mapping is unavailable.')
    if schema_version != expected_schema_version:
        raise RuntimeError('Refusing browser writes: Daily-use schema is not at the expected migration head.')
    return {'container':DAILY_CONTAINER,'database_name':DAILY_DATABASE,'authorized_test_student':str(TEST_STUDENT),'local_user_id':str(student_row['user_id']),'schema_version':schema_version}


def expected_schema_version():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    config=Config(str(ROOT/'alembic.ini'))
    config.set_main_option('script_location',str(ROOT/'migrations'))
    return ScriptDirectory.from_config(config).get_current_head()


def database_preflight(container):
    from sqlalchemy import create_engine,text
    url=database_url(container)
    engine=create_engine(url)
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text('SET TRANSACTION READ ONLY'))
            database_name=connection.execute(text('SELECT current_database()')).scalar_one()
            student_row=connection.execute(text('SELECT s.id::text AS id, s.user_id::text AS user_id FROM students s WHERE s.id=:student_id'),{'student_id':str(TEST_STUDENT)}).mappings().one_or_none()
            schema_version=connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
    return preflight_database_target(container,database_name=database_name,student_row=student_row,schema_version=schema_version,expected_schema_version=expected_schema_version())


def runtime_preflight(api_pid, expected_url):
    result=subprocess.run(['ps','eww','-p',str(api_pid),'-o','command='],capture_output=True,text=True,check=True)
    command=result.stdout.strip()
    if 'uvicorn' not in command or 'apps.api.main:app' not in command or f'DATABASE_URL={expected_url}' not in command:
        raise RuntimeError('Refusing browser writes: running API process is not the guarded Daily-use runtime.')
    return {'api_pid':int(api_pid),'api_origin':API_ORIGIN,'web_origin':WEB_ORIGIN,'model_provider':'mock'}


def requires_preflight(mode):
    return mode in ('api','prepare')


def exits_after_preflight(mode):
    return mode in ('inspect','preflight')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['inspect','preflight','api','prepare','readback'])
    parser.add_argument('--session')
    parser.add_argument('--source')
    parser.add_argument('--api-pid',type=int)
    args=parser.parse_args()
    container=container_metadata()
    url=database_url(container)
    if args.mode in ('inspect','preflight') or requires_preflight(args.mode):
        result=database_preflight(container)
        if args.api_pid is not None:
            result.update(runtime_preflight(args.api_pid,url.render_as_string(hide_password=False)))
        if exits_after_preflight(args.mode):
            print(json.dumps(result));return
    if args.mode=='api':
        env={**os.environ,'MODEL_PROVIDER':'mock','DATABASE_URL':url.render_as_string(hide_password=False),'PYTHONDONTWRITEBYTECODE':'1'}
        os.execve(sys.executable,[sys.executable,'-m','uvicorn','apps.api.main:app','--host','127.0.0.1','--port','8000'],env)
    from sqlalchemy import create_engine,select
    from sqlalchemy.orm import Session
    from services.platform.db.models import Student,LearningSession,LearningMessage,LearningSegment
    with Session(create_engine(url)) as session:
        student=session.get(Student,TEST_STUDENT)
        if student is None:raise RuntimeError('Documented test Student unavailable; no account creation allowed.')
        if not args.session:raise ValueError('Exact session required.')
        learning=session.get(LearningSession,UUID(args.session))
        if learning is None or learning.student_id!=TEST_STUDENT or learning.status!='OPEN':raise ValueError('Prepared setup requires exact open authorized test session.')
        if args.mode=='readback':
            from services.platform.db.models import StudioRuntime,StudioScene,StudioEvent,StudioSnapshot,StudioStudentInteraction,AIExecution
            from services.studio.service import StudioStateService
            runtime=session.execute(select(StudioRuntime).where(StudioRuntime.learning_session_id==learning.id)).scalar_one()
            snapshot=session.execute(select(StudioSnapshot).where(StudioSnapshot.studio_runtime_id==runtime.id)).scalar_one()
            events=list(session.scalars(select(StudioEvent).where(StudioEvent.studio_runtime_id==runtime.id).order_by(StudioEvent.sequence)))
            interactions=list(session.scalars(select(StudioStudentInteraction).where(StudioStudentInteraction.studio_runtime_id==runtime.id)))
            messages=list(session.scalars(select(LearningMessage).where(LearningMessage.session_id==learning.id)))
            executions=list(session.scalars(select(AIExecution).where(AIExecution.learning_session_id==learning.id)))
            rebuild=StudioStateService(session).rebuild_snapshot(runtime_id=runtime.id,student_id=student.id)
            print(json.dumps(dict(session_id=str(learning.id),runtime_id=str(runtime.id),latest_sequence=snapshot.latest_event_sequence,scene_version=snapshot.current_scene_version,
                state=snapshot.state_payload,rebuild_equal=rebuild['state_payload']==snapshot.state_payload,watermark=runtime.last_tutor_observation_sequence,
                events=[dict(id=str(e.id),sequence=e.sequence,scene_id=str(e.scene_id),base_version=e.base_scene_version,resulting_version=e.resulting_scene_version,kind=e.event_kind,action=e.action_key,payload=e.payload,idempotency_key=e.idempotency_key) for e in events],
                interactions=[dict(id=str(i.id),status=i.status,tutor_message_id=str(i.tutor_message_id),ai_execution_id=str(i.ai_execution_id)) for i in interactions],
                executions=[dict(id=str(e.id),task=e.task,provider=e.provider,success=e.success,operation_type=e.operation_type) for e in executions],
                messages=[dict(id=str(m.id),role=m.role,origin=m.payload.get('turn_origin'),prepared=bool(m.payload.get('test_setup'))) for m in messages]),default=str))
            return
        if not args.source:raise ValueError('Exact authored source required.')
        from datetime import datetime, UTC
        from services.tutor.session_lifecycle import session_lifecycle_policy
        if datetime.now(UTC) >= session_lifecycle_policy().closes_at(learning.last_activity_at):
            raise ValueError('Session expired; use the authenticated no-ID path for a fresh eligible session.')
        from services.studio.subjects import decimal_number_line as math,production_subject_registry,PRODUCTION_CURRENT_PROFILE_VERSIONS
        from services.studio.workspace_intent import WorkspaceIntent
        from services.studio.router import WorkspaceAuthorityContext,route_workspace_intent
        from services.studio.activity_activation import activate_known_workspace_activity
        math.problem_for(args.source)
        segment=session.execute(select(LearningSegment).where(LearningSegment.session_id==learning.id).order_by(LearningSegment.sequence.desc())).scalars().first()
        if segment is None:
            segment=LearningSegment(session_id=learning.id,sequence=1);session.add(segment);session.flush()
        intent=WorkspaceIntent.model_validate(dict(version='workspace-intent-v1',action='OPEN_ACTIVITY',subject_key='MATH',activity_hint=math.ACTIVITY_KEY,concept_keys=[],learning_goal=None,representation_need='INTERACTIVE',expected_student_response_mode='WORKSPACE',presentation_sequence='PARALLEL',source_references=[args.source],safe_text_fallback=None))
        decision=route_workspace_intent(intent,WorkspaceAuthorityContext(registry=production_subject_registry(),current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS,authorized_source_references=(args.source,)))
        audit=dict(intent_status='VALID',intent=intent.model_dump(mode='json'),decision=decision.as_audit_payload())
        source=LearningMessage(session_id=learning.id,segment_id=segment.id,role='tutor',content='Prepared number-line test configuration. Place the labelled points, choose an answer, then submit.',payload={'workspace':audit,'test_setup':'MATH-RENDER-NUMBER-LINE-01 prepared authored configuration; not natural model selection'})
        session.add(source);session.flush()
        scene=activate_known_workspace_activity(session,learning_session=learning,source_tutor_message=source,source_segment_id=segment.id,workspace_audit=audit)
        if scene is None:raise RuntimeError('Exact prepared activation declined; transaction not committed.')
        result=dict(session_id=str(learning.id),student_id=str(student.id),source_ref=args.source,source_message_id=str(source.id),scene_id=str(scene.id),runtime_id=str(scene.studio_runtime_id),scene_version=scene.scene_version,setup='PREPARED; NOT NATURAL-MODEL SELECTION')
        session.commit();print(json.dumps(result))


if __name__=='__main__':main()
