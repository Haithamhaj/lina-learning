"""Independent review evidence, ownership, failure ledger and non-mutation contracts."""
import base64
import os
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from services.canvas_review.service import capture_review, analyze_review, get_review, list_reviews, validate_report, ReviewUnavailable
from services.model_gateway.factory import create_canvas_development_review_gateway
from services.model_gateway.gateway import ModelResult, StaticModelProvider, ModelRoute
from services.model_gateway.openai_provider import _request_body
from services.platform.config import Settings
from services.platform.db import models as m
from services.studio.agent.admission import admit_agentic_canvas_brief
from tests.test_agentic_canvas_lifecycle_postgres import factory, _admitted_message

REPORT = {'version': 'canvas-development-review-v1', 'summary': 'لا توجد صورة محفوظة للحكم.',
          'findings': [], 'limitations': ['لا يثبت نجاح التنفيذ صحة التعلم.']}


def test_image_boundary_rejects_external_urls_and_wrong_schema():
    payload = {'instructions': 'review', 'input': '{}', 'review_images': ['https://example.com/private.png'],
               'response_schema': {'name': 'canvas_development_review_v1'}}
    with pytest.raises(ValueError):
        _request_body(ModelRoute('openai', 'fixture'), payload)
    payload['review_images'] = ['data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()]
    assert _request_body(ModelRoute('openai', 'fixture'), payload)['input'][0]['content'][1]['type'] == 'input_image'
    payload['response_schema']['name'] = 'tutor'
    with pytest.raises(ValueError):
        _request_body(ModelRoute('openai', 'fixture'), payload)


def test_report_requires_known_evidence_and_preserves_capture_limits():
    pack = {'evidence': [{'id': 'E001'}], 'limitations': ['No student screen recording']}
    assert 'No student screen recording' in validate_report(REPORT, pack)['limitations']
    report = {**REPORT, 'findings': [{'category': 'VISUAL', 'severity': 'HIGH', 'certainty': 'OBSERVED',
        'claim': 'Wrong scale', 'evidence_refs': ['E999'], 'recommendation': 'Fix scale', 'verification': 'Measure units'}]}
    with pytest.raises(ValueError, match='unavailable evidence'):
        validate_report(report, pack)


@pytest.mark.skipif(not os.getenv('DATABASE_URL'), reason='PostgreSQL required')
@pytest.mark.parametrize('provider_fails', [False, True])
def test_owned_capture_and_analysis_preserve_student_records(factory, provider_fails):
    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        run = admit_agentic_canvas_brief(session, student_id=student.id,
            learning_session_id=learning.id, source_message_id=message.id)
        run.status = 'FAILED'
        student_id, run_id = student.id, run.id
        original_message = message.content
    with pytest.raises(ReviewUnavailable):
        capture_review(factory, storage=None, student_id=uuid4(), run_id=run_id, requested_by='test')
    identity = capture_review(factory, storage=None, student_id=student_id, run_id=run_id, requested_by='test')
    with factory() as session:
        row = get_review(session, student_id=student_id, review_id=identity)
        assert row.status == 'READY'
        assert 'visual_learner_context' not in str(row.evidence_manifest)
        assert original_message not in str(row.evidence_manifest)
        with pytest.raises(ReviewUnavailable):
            get_review(session, student_id=uuid4(), review_id=identity)
    class Provider:
        calls = 0
        def execute(self, route, payload):
            self.calls += 1
            if provider_fails:
                raise RuntimeError('private provider detail')
            return ModelResult(output=REPORT, input_tokens=20, output_tokens=30)
    provider = Provider()
    kwargs = dict(student_id=student_id, review_id=identity, gateway_factory=lambda session:
        create_canvas_development_review_gateway(session, settings=Settings(model_provider='mock'), local_provider=provider))
    if provider_fails:
        with pytest.raises(RuntimeError):
            analyze_review(factory, **kwargs)
    else:
        assert analyze_review(factory, **kwargs)['summary'] == REPORT['summary']
    with pytest.raises(ReviewUnavailable):
        analyze_review(factory, **kwargs)
    assert provider.calls == 1
    with factory() as session:
        row = get_review(session, student_id=student_id, review_id=identity)
        assert row.status == ('FAILED' if provider_fails else 'COMPLETED')
        calls = list(session.scalars(select(m.AIExecution).where(m.AIExecution.operation_id == identity)))
        assert len(calls) == 1 and calls[0].success is not provider_fails
        assert session.get(m.StudioCanvasSpecialistRun, run_id).status == 'FAILED'
        assert session.scalar(select(func.count()).select_from(m.StudioEvent)) == 0
        assert session.scalar(select(m.LearningMessage.content)) == original_message
        assert session.scalar(select(func.count()).select_from(m.CanvasDevelopmentReview)) == 1
        history = list_reviews(session, student_id=student_id, run_id=run_id)
        assert [item['id'] for item in history] == [str(identity)]
        if not provider_fails:
            assert row.report['reviewer']['model'] == 'mock'
            assert row.report['reviewer']['review_version'] == 'canvas-development-review-v1'
    second_identity = capture_review(
        factory, storage=None, student_id=student_id, run_id=run_id, requested_by='comparison-test'
    )
    with factory() as session:
        history = list_reviews(session, student_id=student_id, run_id=run_id)
        assert [item['id'] for item in history] == [str(second_identity), str(identity)]
        assert get_review(session, student_id=student_id, review_id=identity).status == (
            'FAILED' if provider_fails else 'COMPLETED'
        )


def test_technical_capture_excludes_privileged_nested_context():
    from services.canvas_review.service import technical_data
    value = {'status': 'ok', 'tools': [{'visual_learner_context': {'secret': 'x'}, 'action': 'MOVE'}],
             'bridge_nonce': 'private', 'context_payload': {'student': 'original'}}
    assert technical_data(value) == {'status': 'ok', 'tools': [{'action': 'MOVE'}]}


@pytest.mark.skipif(not os.getenv('DATABASE_URL'), reason='PostgreSQL required')
def test_tampered_pack_rejected_before_provider_and_wrong_owner_cannot_analyze(factory):
    with factory.begin() as session:
        student, learning, message = _admitted_message(session)
        run = admit_agentic_canvas_brief(session, student_id=student.id,
            learning_session_id=learning.id, source_message_id=message.id)
        student_id, run_id = student.id, run.id
    identity = capture_review(factory, storage=None, student_id=student_id, run_id=run_id, requested_by='test')
    def forbidden_gateway(session):
        pytest.fail('Provider must not be constructed')
    with pytest.raises(ReviewUnavailable):
        analyze_review(factory, student_id=uuid4(), review_id=identity, gateway_factory=forbidden_gateway)
    with factory.begin() as session:
        row = get_review(session, student_id=student_id, review_id=identity)
        row.evidence_manifest = {**row.evidence_manifest, 'sha256': '0' * 64}
    with pytest.raises(ValueError, match='integrity'):
        analyze_review(factory, student_id=student_id, review_id=identity, gateway_factory=forbidden_gateway)
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(m.AIExecution).where(m.AIExecution.operation_id == identity)) == 0
