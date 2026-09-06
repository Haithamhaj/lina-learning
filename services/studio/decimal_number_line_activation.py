"""Exact authored-problem activation from a persisted normal Tutor audit."""
import logging
from collections.abc import Mapping
from sqlalchemy import select
from services.platform.db.models import LearningMessage, StudioScene
from services.studio.contracts import AppendStudioEventCommand, CreateSceneCommand, StudioActor
from services.studio.reducer import CORE_EVENT_SCHEMA_VERSION
from services.studio.service import StudioStateService, StudioStateError
from services.studio.subjects import decimal_number_line as math

logger = logging.getLogger(__name__)


def activate_decimal_number_line(session, *, learning_session, source_tutor_message, source_segment_id, workspace_audit):
    if not isinstance(workspace_audit, Mapping) or workspace_audit.get('intent_status') != 'VALID':
        return None
    intent, decision = workspace_audit.get('intent'), workspace_audit.get('decision')
    if not isinstance(intent, Mapping) or not isinstance(decision, Mapping):
        return None
    if not all(decision.get(k) == v for k,v in dict(status='ROUTED', mode='KNOWN_INTERACTIVE', reason_code='EXACT_KNOWN_CAPABILITY',
        selected_subject_key='MATH', selected_profile_version=math.PROFILE_VERSION, selected_activity_key=math.ACTIVITY_KEY,
        selected_activity_version=math.ACTIVITY_VERSION, selected_renderer_key=math.RENDERER_KEY, selected_renderer_version=math.RENDERER_VERSION).items()):
        return None
    ref = decision.get('target_source_reference')
    if intent.get('action') != 'OPEN_ACTIVITY' or intent.get('subject_key') != 'MATH' or intent.get('activity_hint') != math.ACTIVITY_KEY or intent.get('source_references') != [ref]:
        return None
    try:
        seed = math.scene_seed(ref)
    except ValueError:
        return None
    # Read the persisted source, not merely the caller's in-memory audit object.
    persisted = session.execute(select(LearningMessage).where(LearningMessage.id==source_tutor_message.id)).scalar_one_or_none()
    if persisted is None or persisted.role != 'tutor' or persisted.session_id != learning_session.id or persisted.segment_id != source_segment_id or persisted.payload.get('workspace') != workspace_audit:
        return None
    try:
        # Replacement and acceptance are atomic: failure leaves the old scene usable.
        with session.begin_nested():
            state = StudioStateService(session)
            runtime = state.get_or_create_runtime(student_id=learning_session.student_id, learning_session_id=learning_session.id)
            active = session.execute(select(StudioScene).where(StudioScene.studio_runtime_id==runtime.id,StudioScene.status=='ACTIVE').with_for_update()).scalar_one_or_none()
            def lifecycle(scene, kind, payload, suffix):
                state.append_event(AppendStudioEventCommand(runtime_id=runtime.id, student_id=learning_session.student_id, learning_session_id=learning_session.id,
                    event_kind='studio.scene.'+kind, event_schema_version=CORE_EVENT_SCHEMA_VERSION, actor=StudioActor.SYSTEM,
                    payload_schema_version='studio-scene-'+kind.replace('_','-')+'-v1', payload=payload, scene_id=scene.id,
                    base_scene_version=scene.scene_version,source_message_id=persisted.id,source_segment_id=source_segment_id,
                    idempotency_key=f'decimal-line:{persisted.id}:{suffix}'))
            if active is not None:
                if (active.subject_key,active.subject_profile_version,active.activity_key,active.activity_contract_version,active.renderer_key,active.renderer_version,active.payload_schema_version)==('MATH',math.PROFILE_VERSION,math.ACTIVITY_KEY,math.ACTIVITY_VERSION,math.RENDERER_KEY,math.RENDERER_VERSION,math.SEED_VERSION) and active.seed_payload == seed:
                    return active
                lifecycle(active,'status_changed',{'status':'SUPERSEDED'},'replace')
            scene = state.accept_scene(CreateSceneCommand(student_id=learning_session.student_id,learning_session_id=learning_session.id,
                subject_key='MATH',subject_profile_version=math.PROFILE_VERSION,concept_keys=('decimal-number-line',),activity_key=math.ACTIVITY_KEY,
                artifact_type='interactive-activity',renderer_key=math.RENDERER_KEY,renderer_version=math.RENDERER_VERSION,activity_contract_version=math.ACTIVITY_VERSION,
                payload_schema_version=math.SEED_VERSION,seed_payload=seed,accessibility_payload={'axis_direction':'ltr','exact_controls':True},
                locale='en',direction='auto',source_message_id=persisted.id,source_segment_id=source_segment_id))
            lifecycle(scene,'activated',{},'activate')
            return scene
    except (StudioStateError, ValueError):
        logger.warning('Authored number-line activation declined safely.',exc_info=True)
        return None
