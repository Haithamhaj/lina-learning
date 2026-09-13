"""Operator-only, on-demand engineering review. No student runtime hooks."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import select

from services.canvas_review.contracts import DevelopmentReport, INSTRUCTIONS, REVIEW_VERSION, validate_images
from services.model_gateway.gateway import AIExecutionLineage
from services.platform.db import models as m
from services.studio.custom_visual_builds import CustomVisualBuildResolver
from services.studio.custom_visual_preview import preview_custom_visual


class ReviewUnavailable(ValueError):
    pass


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()


def technical_data(value):
    """Defense in depth: exclude privileged runtime context from copied diagnostics."""
    excluded = {'visual_learner_context', 'selected_personal_facts', 'personal_facts',
        'intelligence_card', 'raw_transcript', 'conversation', 'context_payload',
        'bridge_nonce', 'authorization', 'api_key', 'access_token'}
    if isinstance(value, dict):
        return {k: technical_data(v) for k, v in value.items() if k.lower() not in excluded}
    if isinstance(value, list):
        return [technical_data(v) for v in value]
    return value


def fields(row, names):
    return json.loads(encoded({name: getattr(row, name) for name in names}))


def list_experiences(session, *, student_id: UUID, limit=50, offset=0):
    if not 1 <= limit <= 100 or offset < 0:
        raise ValueError("Invalid page")
    rows = session.scalars(select(m.StudioCanvasSpecialistRun).where(
        m.StudioCanvasSpecialistRun.student_id == student_id
    ).order_by(m.StudioCanvasSpecialistRun.created_at.desc(), m.StudioCanvasSpecialistRun.id).limit(limit).offset(offset))
    return [fields(row, ('id', 'status', 'subject_key', 'scene_id', 'created_at', 'completed_at')) for row in rows]


def list_reviews(session, *, student_id: UUID, run_id: UUID | None = None, limit=50, offset=0):
    """Return immutable review history without exposing its private evidence pack."""
    if not 1 <= limit <= 100 or offset < 0:
        raise ValueError("Invalid page")
    query = select(m.CanvasDevelopmentReview).where(
        m.CanvasDevelopmentReview.student_id == student_id
    )
    if run_id is not None:
        query = query.where(m.CanvasDevelopmentReview.run_id == run_id)
    rows = session.scalars(query.order_by(
        m.CanvasDevelopmentReview.created_at.desc(), m.CanvasDevelopmentReview.id
    ).limit(limit).offset(offset))
    return [fields(row, (
        'id', 'run_id', 'status', 'requested_by', 'schema_version', 'ai_execution_id',
        'failure_code', 'created_at', 'completed_at'
    )) for row in rows]


def get_review(session, *, student_id, review_id, lock=False):
    query = select(m.CanvasDevelopmentReview).where(
        m.CanvasDevelopmentReview.id == review_id, m.CanvasDevelopmentReview.student_id == student_id)
    row = session.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise ReviewUnavailable("Review unavailable")
    return row


def capture_review(factory, *, storage, student_id, run_id, requested_by, preview=True,
                   preview_fn=preview_custom_visual):
    """Snapshot bounded evidence in one owned DB record; images have no public URL.

    Source packages are read through the existing ownership/integrity resolver.
    The bounded pack lives in the review row so deletion cannot orphan copies.
    """
    if not isinstance(requested_by, str) or not 1 <= len(requested_by.strip()) <= 120:
        raise ValueError("Operator attribution is required")
    review_id = uuid4()
    with factory() as session:
        run = session.scalar(select(m.StudioCanvasSpecialistRun).where(
            m.StudioCanvasSpecialistRun.id == run_id, m.StudioCanvasSpecialistRun.student_id == student_id))
        if run is None:
            raise ReviewUnavailable("Run unavailable")
        row = m.CanvasDevelopmentReview(id=review_id, run_id=run.id, studio_runtime_id=run.studio_runtime_id,
            student_id=run.student_id, learning_session_id=run.learning_session_id, status='CAPTURING',
            requested_by=requested_by.strip(), schema_version=REVIEW_VERSION, evidence_manifest={})
        session.add(row)
        session.commit()
    try:
        evidence = []
        limitations = [
            'This is a bounded capture at review time, not continuous screen recording.',
            'Preview actions are synthetic reproduction, not replay of the student session.',
            'No raw conversation, personal facts, mastery or learning-benefit evaluation is included.',
            'Only persisted Specialist runs are indexed; chat-only/non-Specialist activity is outside coverage.',
        ]
        def add(kind, data):
            identity = f'E{len(evidence)+1:03d}'
            evidence.append({'id': identity, 'kind': kind, 'data': data})
            return identity
        packages = []
        event_ids = []
        with factory() as session:
            run = session.scalar(select(m.StudioCanvasSpecialistRun).where(
                m.StudioCanvasSpecialistRun.id == run_id, m.StudioCanvasSpecialistRun.student_id == student_id))
            if run is None:
                raise ReviewUnavailable('Run unavailable')
            add('run', fields(run, ('status','subject_key','base_scene_version','accepted_scene_version',
                'output_schema_version','order_digest','proposal_digest','created_at','started_at','completed_at')))
            # Technical metadata may contain model-generated text: bounded, never trusted instructions.
            metadata = technical_data({'failure': run.failure_metadata, 'execution': run.agent_execution_metadata})
            if len(encoded(metadata)) <= 100_000:
                add('operational_diagnostics', metadata)
            else:
                limitations.append('Operational diagnostics exceeded 100 KB and were omitted.')
            message = session.get(m.LearningMessage, run.source_message_id)
            if message and message.session_id == run.learning_session_id:
                brief = (message.payload or {}).get('agentic_canvas', {}).get('brief')
                if brief and len(encoded(brief)) <= 32_000:
                    add('admitted_brief', brief)
            scene = session.get(m.StudioScene, run.scene_id) if run.scene_id else None
            if scene and scene.student_id == student_id and scene.studio_runtime_id == run.studio_runtime_id:
                add('scene_identity', fields(scene, ('id','scene_version','renderer_key','renderer_version','accepted_at')))
                blocks = scene.seed_payload.get('blocks', [])
                for block in blocks[:8]:
                    if block.get('type') != 'CUSTOM_VISUAL':
                        limitations.append('Typed/image blocks are not visually reproduced in this review version.')
                        continue
                    if len(packages) >= 1:
                        limitations.append('Only the first custom block is reproduced; remaining blocks omitted.')
                        break
                    build_id = block.get('custom_visual_build_id')
                    if not build_id:
                        limitations.append('Legacy inline package is outside immutable Build capture coverage.')
                        continue
                    resolved = CustomVisualBuildResolver(storage).resolve(session, build_id=UUID(build_id),
                        student_id=student_id, runtime_id=run.studio_runtime_id)
                    package = resolved.package
                    build = session.get(m.VisualArtifactBuild, UUID(build_id))
                    data = {'build_id': build_id, 'parameters': block.get('parameters', {}),
                            'manifest_digest': resolved.manifest_digest,
                            'source_digest': build.source_digest if build is not None else None,
                            'bundle_digest': build.bundle_digest if build is not None else None,
                            'validation_status': build.status if build is not None else None}
                    if len(encoded(data)) > 200_000:
                        limitations.append('Build reference exceeds 200 KB review limit; omitted.')
                        continue
                    add('immutable_build', data)
                    # Source is resolved only for this preview operation. The review
                    # record keeps the immutable Build reference and digests, not a
                    # second copy of generated source.
                    packages.append((package, data['parameters']))
                instance = session.scalar(select(m.VisualArtifactInstance).where(
                    m.VisualArtifactInstance.studio_scene_id == scene.id,
                    m.VisualArtifactInstance.student_id == student_id
                ))
                if instance is not None and instance.artifact_version_id is not None:
                    version = session.get(m.VisualArtifactVersion, instance.artifact_version_id)
                    if version is not None:
                        add('artifact_version', fields(version, (
                            'id', 'artifact_id', 'parent_version_id', 'implementation_build_id',
                            'version_number', 'source_digest', 'runtime_contract_version',
                            'validation_status', 'created_at'
                        )))
                events = list(session.scalars(select(m.StudioEvent).where(
                    m.StudioEvent.student_id == student_id, m.StudioEvent.scene_id == scene.id,
                    m.StudioEvent.studio_runtime_id == run.studio_runtime_id
                ).order_by(m.StudioEvent.sequence).limit(101)))
                if len(events) > 100:
                    limitations.append('Event coverage truncated to the first 100 Scene events.')
                event_ids = [event.id for event in events[:100]]
                for event in events[:100]:
                    data = fields(event, ('id','sequence','event_kind','action_key','actor',
                        'base_scene_version','resulting_scene_version','occurred_at'))
                    # Capture canonical technical action payload, bounded. No chat/context payload.
                    if len(encoded(event.payload)) <= 8_000:
                        data['payload'] = technical_data(event.payload)
                    else:
                        data['payload_omitted'] = True
                    add('recorded_event', data)
            else:
                limitations.append('No accepted Scene is available; no visual outcome can be assessed.')
            interactions = list(session.scalars(select(m.StudioStudentInteraction).where(
                m.StudioStudentInteraction.student_id == student_id,
                m.StudioStudentInteraction.studio_runtime_id == run.studio_runtime_id,
                m.StudioStudentInteraction.source_event_id.in_(event_ids)
            ).order_by(m.StudioStudentInteraction.created_at).limit(101)))
            if len(interactions) > 100:
                limitations.append('Tutor continuation coverage truncated to 100 interactions linked to captured Scene events.')
            for interaction in interactions[:100]:
                add('runtime_tutor_continuation', fields(interaction, ('id','status','source_event_id',
                    'tutor_message_id','ai_execution_id','created_at','completed_at')))
            calls = list(session.scalars(select(m.AIExecution).where(
                m.AIExecution.operation_id == run.id, m.AIExecution.student_id == student_id
            ).order_by(m.AIExecution.created_at).limit(101)))
            if len(calls) > 100:
                limitations.append('Model execution coverage truncated to 100 calls.')
            for call in calls[:100]:
                add('model_execution', fields(call, ('id','task','provider','model','success','failure_code',
                    'latency_ms','input_tokens','output_tokens','estimated_cost_usd')))
        images = []
        for package, parameters in packages:
            if not preview:
                limitations.append('Browser reproduction was explicitly disabled.')
                continue
            try:
                result = preview_fn(source=package.source, parameters=parameters, manifest=package.manifest)
                for view in result.get('views', [])[:6]:
                    view = dict(view)
                    url = view.pop('image_url', None)
                    ref = add('fresh_reproduction_view', view)
                    if url:
                        validate_images([url])
                        images.append({'evidence_ref': ref, 'image_url': url, 'sha256': sha256(url.encode()).hexdigest()})
                add('reproduction_checks', {k: v for k, v in result.items() if k != 'views'})
            except Exception as error:
                limitations.append(f'Browser reproduction unavailable: {type(error).__name__}.')
        pack = {'version': REVIEW_VERSION, 'captured_at': datetime.now(UTC).isoformat(),
                'evidence': evidence, 'images': images, 'limitations': limitations,
                'review_instructions_sha256': sha256(INSTRUCTIONS.encode()).hexdigest()}
        if len(encoded(pack)) > 4_000_000:
            raise ValueError('Evidence capture exceeds 4 MB')
        with factory() as session:
            row = get_review(session, student_id=student_id, review_id=review_id, lock=True)
            row.evidence_manifest = {'sha256': sha256(encoded(pack)).hexdigest(), 'pack': pack}
            row.status = 'READY'
            session.commit()
    except Exception as error:
        _fail(factory, student_id, review_id, type(error).__name__)
        raise
    return review_id



def validate_report(output, pack):
    report = DevelopmentReport.model_validate(output)
    known = {item['id'] for item in pack['evidence']}
    if any(ref not in known for finding in report.findings for ref in finding.evidence_refs):
        raise ValueError('Report cites unavailable evidence')
    # Model cannot silently omit the capture's material limitations.
    result = report.model_dump(mode='json')
    result['limitations'] = list(dict.fromkeys([*result['limitations'], *pack['limitations']]))
    return result


def _fail(factory, student_id, review_id, code):
    with factory() as session:
        row = get_review(session, student_id=student_id, review_id=review_id, lock=True)
        row.status, row.failure_code, row.completed_at = 'FAILED', code[:80], datetime.now(UTC)
        session.commit()


def _review_source_input(session, *, storage, row, pack):
    """Resolve immutable source only for the on-demand model request."""
    source_by_ref = {}
    for item in pack['evidence']:
        if item['kind'] != 'immutable_build':
            continue
        data = item['data']
        resolved = CustomVisualBuildResolver(storage).resolve(
            session, build_id=UUID(data['build_id']), student_id=row.student_id,
            runtime_id=row.studio_runtime_id
        )
        if resolved.manifest_digest != data['manifest_digest']:
            raise ValueError('Immutable Build manifest changed unexpectedly')
        if len(resolved.package.source.encode()) > 200_000:
            raise ValueError('Immutable Build source exceeds on-demand review limit')
        source_by_ref[item['id']] = {
            'source': resolved.package.source,
            'manifest': resolved.package.manifest.model_dump(mode='json'),
            'parameters': data['parameters'],
        }
    return source_by_ref


def analyze_review(factory, *, student_id, review_id, gateway_factory, storage=None):
    with factory() as session:
        row = get_review(session, student_id=student_id, review_id=review_id, lock=True)
        if row.status != 'READY':
            raise ReviewUnavailable('Only a READY review can be analyzed; create a new capture for another review')
        manifest = row.evidence_manifest
        pack = manifest['pack']
        if sha256(encoded(pack)).hexdigest() != manifest['sha256']:
            raise ValueError('Evidence integrity failure')
        learning_session_id = row.learning_session_id
        row.status = 'RUNNING'
        session.commit()
    try:
        images = [item['image_url'] for item in pack['images']]
        validate_images(images)
        with factory() as session:
            row = get_review(session, student_id=student_id, review_id=review_id)
            source_by_ref = _review_source_input(session, storage=storage, row=row, pack=pack)
        text_pack = {**pack, 'images': [{k:v for k,v in item.items() if k != 'image_url'} for item in pack['images']],
                     'resolved_source_for_review_only': source_by_ref}
        payload = {'instructions': INSTRUCTIONS, 'input': encoded(text_pack).decode(),
            'max_output_tokens': 6000, 'review_images': images,
            'response_schema': {'name': 'canvas_development_review_v1', 'schema': DevelopmentReport.model_json_schema()}}
        with factory() as session:
            try:
                result = gateway_factory(session).execute(m.ModelTask.CANVAS_DEVELOPMENT_REVIEW, payload,
                    lineage=AIExecutionLineage(operation='canvas_development_review', operation_id=review_id,
                        student_id=student_id, learning_session_id=learning_session_id))
            finally:
                # Preserve provider failure/usage records even if schema validation fails later.
                session.commit()
            row = get_review(session, student_id=student_id, review_id=review_id)
            row.ai_execution_id = result.execution_id
            session.commit()
        report = validate_report(result.output, pack)
        with factory() as session:
            row = get_review(session, student_id=student_id, review_id=review_id, lock=True)
            execution = session.get(m.AIExecution, row.ai_execution_id)
            row.report = {**report, 'reviewer': {
                'review_version': REVIEW_VERSION,
                'instructions_sha256': pack['review_instructions_sha256'],
                'provider': execution.provider if execution is not None else None,
                'model': execution.model if execution is not None else None,
                'execution_id': str(row.ai_execution_id) if row.ai_execution_id is not None else None,
            }}
            row.status, row.completed_at = 'COMPLETED', datetime.now(UTC)
            session.commit()
        return report
    except Exception as error:
        _fail(factory, student_id, review_id, type(error).__name__)
        raise
