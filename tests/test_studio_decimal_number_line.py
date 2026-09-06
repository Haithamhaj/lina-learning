"""Exact domain and wrong-attempt contracts for the bounded decimal line."""
from decimal import Decimal, ROUND_HALF_UP
from importlib import import_module

import pytest


def module():
    try:
        return import_module('services.studio.subjects.decimal_number_line')
    except ModuleNotFoundError:
        pytest.fail('Production decimal number-line capability is missing')


def test_rounding_agrees_with_decimal_half_up_for_every_supported_value():
    m = module()
    for value in range(10001):
        for place, exponent in [('ones', '1'), ('tenths', '0.1'), ('hundredths', '0.01')]:
            want = int((Decimal(value) / 1000).quantize(Decimal(exponent), rounding=ROUND_HALF_UP) * 1000)
            assert m.round_value(value, place) == want


@pytest.mark.parametrize('value', [True, -1, 10001, 0.5, '500', None])
def test_unsupported_values_are_rejected(value):
    with pytest.raises(ValueError):
        module().round_value(value, 'hundredths')


def test_equal_decimal_forms_preserve_two_point_identities():
    seed = module().scene_seed('decimal-line:v1:compare-equal')
    assert [(p['id'], p['value'], p['text']) for p in seed['points']] == [('a', 500, '0.5'), ('b', 500, '0.500')]
    assert seed['positions'] == {'a': None, 'b': None}
    assert 'answer' not in seed and 'correct_answer' not in seed


def test_wrong_allowed_placement_is_recordable_but_mismatch_is_rejected():
    m = module()
    state = {'scene_seed': m.scene_seed('decimal-line:v1:compare-less')}
    result = m.validate_place({'action': {'point_id': 'a', 'from_value': None, 'value': 499}, 'activity_state': state})
    assert result.status.value == 'VALID'
    with pytest.raises(ValueError):
        m.validate_place({'action': {'point_id': 'a', 'from_value': 444, 'value': 499}, 'activity_state': state})


def test_submit_distinguishes_incomplete_malformed_and_academically_wrong():
    m = module()
    seed = m.scene_seed('decimal-line:v1:compare-less')
    current = {'positions': {'a': 499, 'b': 446}, 'selection': 'GT'}
    payload = {'action': {'source_ref': seed['source_ref'], **current}, 'activity_state': {'scene_seed': seed, m.ACTIVITY_KEY: current}}
    assert m.validate_submit(payload).status.value == 'INVALID'
    payload['action']['positions'] = {'a': 444, 'b': 446}
    with pytest.raises(ValueError):
        m.validate_submit(payload)
    payload['activity_state'][m.ACTIVITY_KEY] = {'positions': {'a': 444, 'b': 446}, 'selection': 'LT'}
    payload['action']['selection'] = 'LT'
    assert m.validate_submit(payload).status.value == 'VALID'


def test_profile_dispatch_preserves_make_ten_and_rebuilds_original_submission():
    from types import SimpleNamespace
    from services.studio.subjects import production_subject_registry, PRODUCTION_CURRENT_PROFILE_VERSIONS
    m = module()
    registry = production_subject_registry()
    profile = registry.resolve_profile('MATH', PRODUCTION_CURRENT_PROFILE_VERSIONS['MATH'])
    assert {a.activity_key for a in profile.activities} == {'ten_frame_group_transfer', m.ACTIVITY_KEY, 'decimal_place_value'}
    assert {a.activity_key for a in registry.resolve_profile('MATH','subject-profile-v3').activities} == {'ten_frame_group_transfer',m.ACTIVITY_KEY}
    assert registry.resolve_profile('MATH', 'subject-profile-v2').activities[0].activity_key == 'ten_frame_group_transfer'
    snapshot = {'latest_event_sequence': 2, 'state_payload': {'scene_seed': m.scene_seed('decimal-line:v1:compare-less')}}
    events = [('PLACE_POINT', {'point_id': 'a', 'from_value': None, 'value': 444}),
              ('PLACE_POINT', {'point_id': 'b', 'from_value': None, 'value': 446}),
              ('SELECT_ANSWER', {'from_selection': None, 'selection': 'LT'}),
              ('SUBMIT_CONFIGURATION', {'source_ref': 'decimal-line:v1:compare-less', 'positions': {'a':444,'b':446}, 'selection':'LT'}),
              ('PLACE_POINT', {'point_id':'a','from_value':444,'value':499})]
    for sequence, (key, payload) in enumerate(events, 3):
        snapshot = m.reduce_attempt(snapshot, SimpleNamespace(sequence=sequence, actor='STUDENT', action_key=key, payload=payload, id=str(sequence)))
    state = snapshot['state_payload'][m.ACTIVITY_KEY]
    assert state['positions']['a'] == 499
    assert state['last_submission']['positions']['a'] == 444
    assert state['last_validation']['status'] == 'VALID'


def test_authored_source_route_requires_one_exact_binding_and_reuses_only_same_problem():
    from services.studio.router import WorkspaceAuthorityContext, ActiveSceneCapability, route_workspace_intent
    from services.studio.workspace_intent import WorkspaceIntent
    from services.studio.subjects import production_subject_registry, PRODUCTION_CURRENT_PROFILE_VERSIONS
    m = module()
    a, b = 'decimal-line:v1:compare-less', 'decimal-line:v1:compare-equal'
    intent = WorkspaceIntent.model_validate(dict(version='workspace-intent-v1', action='OPEN_ACTIVITY', subject_key='MATH', activity_hint=m.ACTIVITY_KEY,
        concept_keys=[], learning_goal=None, representation_need='INTERACTIVE', expected_student_response_mode='WORKSPACE', presentation_sequence='PARALLEL', source_references=[a], safe_text_fallback=None))
    ctx = WorkspaceAuthorityContext(registry=production_subject_registry(), current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS, authorized_source_references=(a,b))
    decision = route_workspace_intent(intent, ctx)
    assert decision.target_source_reference == a
    for refs in ([], [a,b], ['unknown']):
        assert route_workspace_intent(intent.model_copy(update={'source_references': refs}), ctx).status.value == 'FALLBACK'
    from dataclasses import replace
    ctx = replace(ctx, active_scene=ActiveSceneCapability('scene-a','MATH',m.PROFILE_VERSION,m.ACTIVITY_KEY,m.ACTIVITY_VERSION,m.RENDERER_KEY,m.RENDERER_VERSION, (a,)))
    assert route_workspace_intent(intent, ctx).status.value == 'PRESERVE_ACTIVE_SCENE'
    assert route_workspace_intent(intent.model_copy(update={'source_references':[b]}), ctx).status.value == 'ROUTED'


def test_authored_catalog_is_advertised_as_problem_sources_not_retrieval_citations():
    from services.studio.workspace_capabilities import build_workspace_capability_context
    from services.studio.tutor_context import StudioTutorWorkspaceContext
    ctx = StudioTutorWorkspaceContext(runtime_id='test', snapshot_sequence=0, snapshot_schema_version='studio-snapshot-v1', through_sequence=0, current_scene_id=None, current_scene_version=None,
        active_subject_key='MATH', active_activity_key=None, state_payload={}, unseen_events=(), observation_id=None)
    result = build_workspace_capability_context(ctx, authorized_source_references=('retrieval-1',)).as_model_payload()
    assert 'decimal-line:v1:compare-equal' in result['authorized_source_references']
    assert result['authored_problem_sources'][1]['source_ref'] == 'decimal-line:v1:compare-equal'
    assert result['authored_problem_sources'][1]['points'][0]['value'] == 500


def test_authored_problem_references_are_not_source_view_or_annotation_assets():
    from services.studio.router import WorkspaceAuthorityContext, route_workspace_intent
    from services.studio.workspace_intent import WorkspaceIntent
    ref='decimal-line:v1:compare-equal'
    for action,need in [('FOCUS_SOURCE','SOURCE'),('REQUEST_ANNOTATION','ANNOTATION')]:
        intent=WorkspaceIntent.model_validate(dict(version='workspace-intent-v1',action=action,subject_key='MATH',activity_hint=None,concept_keys=[],learning_goal=None,representation_need=need,expected_student_response_mode='WORKSPACE',presentation_sequence='PARALLEL',source_references=[ref],safe_text_fallback=None))
        assert route_workspace_intent(intent,WorkspaceAuthorityContext(authorized_source_references=(ref,))).status.value=='FALLBACK'


def test_make_ten_current_and_historical_activation_contracts_remain_exact():
    from services.studio.make_ten_activation import _is_exact_make_ten_open
    from test_studio_make_ten_postgres import _make_ten_workspace_audit
    audit = _make_ten_workspace_audit()
    assert _is_exact_make_ten_open(audit)
    audit['decision']['selected_profile_version'] = 'subject-profile-v2'
    assert _is_exact_make_ten_open(audit)
    audit['decision']['selected_profile_version'] = 'subject-profile-v999'
    assert not _is_exact_make_ten_open(audit)


def test_first_scene_sources_use_explicit_current_subject_not_a_default():
    from services.studio.workspace_capabilities import build_workspace_capability_context
    from services.studio.tutor_context import StudioTutorWorkspaceContext
    ctx=StudioTutorWorkspaceContext(runtime_id='r',snapshot_sequence=0,snapshot_schema_version='studio-snapshot-v1',through_sequence=0,current_scene_id=None,current_scene_version=None,active_subject_key=None,active_activity_key=None,state_payload={},unseen_events=(),observation_id=None)
    sources=build_workspace_capability_context(ctx,authorized_source_references=(),current_subject_key='MATH').authored_problem_sources
    assert len([s for s in sources if s['activity_hint']=='decimal_number_line'])==11
    assert len([s for s in sources if s['activity_hint']=='decimal_place_value'])==12
    assert build_workspace_capability_context(ctx,authorized_source_references=(),current_subject_key=None).authored_problem_sources==()
