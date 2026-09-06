"""Hand-calculated conservation, incomplete-attempt and strict input cases."""
import importlib
from copy import deepcopy

import pytest


def module():
    try:
        return importlib.import_module('services.studio.subjects.decimal_place_value')
    except ModuleNotFoundError:
        pytest.fail('Decimal place-value behavior is not implemented')


def apply(m, seed, attempt, key, **fields):
    return m.transition(seed, attempt, key, {'from_pools': deepcopy(attempt['pools']), **fields})


def test_addition_two_carries_conserves_disjoint_operands():
    m = module(); seed = m.scene_seed('decimal-place:v1:add-carry')
    attempt = m.initial_attempt(seed)
    for pool in ('a', 'b'):
        for place, count in list(attempt['pools'][pool].items()):
            if count:
                attempt = apply(m, seed, attempt, 'TRANSFER', source=pool, target='result', place=place, count=count)
    assert attempt['pools']['result']==dict(hundreds=0,tens=0,ones=1,tenths=10,hundredths=12)
    attempt = apply(m, seed, attempt, 'EXCHANGE', pool='result', place='hundredths', direction='UP')
    attempt = apply(m, seed, attempt, 'EXCHANGE', pool='result', place='tenths', direction='UP')
    assert attempt['pools']['result']==dict(hundreds=0,tens=0,ones=2,tenths=1,hundredths=2)
    assert m.pool_value(attempt['pools']['result']) == 212
    attempt['result'] = 212
    assert m.feedback(seed, attempt) == dict(structural_valid=True, model_complete=True, model_correct=True, written_correct=True)


def test_subtraction_zero_column_and_regrouping():
    m=module(); seed=m.scene_seed('decimal-place:v1:subtract-zero-chain'); attempt=m.initial_attempt(seed)
    attempt=apply(m,seed,attempt,'EXCHANGE',pool='remaining',place='ones',direction='DOWN')
    attempt=apply(m,seed,attempt,'EXCHANGE',pool='remaining',place='tenths',direction='DOWN')
    assert attempt['pools']['remaining']==dict(hundreds=0,tens=0,ones=1,tenths=9,hundredths=10)
    attempt=apply(m,seed,attempt,'TRANSFER',source='remaining',target='removed',place='tenths',count=7)
    attempt=apply(m,seed,attempt,'TRANSFER',source='remaining',target='removed',place='hundredths',count=5)
    assert m.pool_value(attempt['pools']['remaining'])==125
    assert m.pool_value(attempt['pools']['removed'])==75
    attempt['result']=125
    assert all(m.feedback(seed,attempt).values())
    with pytest.raises(ValueError):
        apply(m,seed,attempt,'TRANSFER',source='remaining',target='removed',place='hundredths',count=1)


@pytest.mark.parametrize('text,expected',[('1.2',120),('1.20',120),('٠',0),('۲٫۱۲',212),('199.98',19998)])
def test_exact_numeric_entry(text,expected):
    assert module().parse_result(text)==expected


@pytest.mark.parametrize('text',['','1.',' 1','01','1e2','1.001','200','-0','1,25','1.2x','.5'])
def test_reject_partial_or_out_of_domain_numeric_entry(text):
    with pytest.raises(ValueError): module().parse_result(text)


def test_incomplete_and_wrong_results_are_feedback_not_malformed():
    m=module(); seed=m.scene_seed('decimal-place:v1:add-carry'); attempt=m.initial_attempt(seed)
    assert m.feedback(seed,attempt)==dict(structural_valid=True,model_complete=False,model_correct=False,written_correct=None)
    attempt['result']=212
    assert m.feedback(seed,attempt)['written_correct'] is True
    assert m.feedback(seed,attempt)['model_complete'] is False
    for bad in (-1,True,1.0,20000):
        broken=deepcopy(attempt);broken['pools']['a']['ones']=bad
        with pytest.raises(ValueError):m.validate_attempt(seed,broken)


def test_registry_submission_and_durable_reducer_preserve_original_attempt():
    from services.studio.subjects import production_subject_registry
    from services.studio.subjects.contracts import ValidationStatus
    from types import SimpleNamespace
    m=module(); registry=production_subject_registry()
    seed=m.scene_seed('decimal-place:v1:subtract-zero-chain')
    action=dict(source_ref=seed['source_ref'],pools=seed['pools'],result=None)
    try:
        contract,validation=registry.validate_subject_event(subject_key='MATH',subject_profile_version='subject-profile-v4',activity_key=m.ACTIVITY_KEY,activity_version=m.ACTIVITY_VERSION,action_key='SUBMIT_CONFIGURATION',payload_schema_version='decimal-place-value-submit-payload-v1',payload=action,activity_state={'scene_seed':seed})
    except ValueError as error:
        pytest.fail(f'Place-value exact registry not available: {error}')
    assert validation.status==ValidationStatus.UNDER_SPECIFIED
    assert contract.interaction_kind=='MATH_DECIMAL_PLACE_VALUE_SUBMISSION'
    reduced=m.reduce_attempt(dict(latest_event_sequence=1,state_payload={'scene_seed':seed}),SimpleNamespace(sequence=2,actor='STUDENT',id='event',action_key='SUBMIT_CONFIGURATION',payload=action))
    assert reduced['state_payload'][m.ACTIVITY_KEY]['last_submission']==action
    assert reduced['state_payload'][m.ACTIVITY_KEY]['last_validation']['model_complete'] is False


@pytest.mark.parametrize('key,want',[('add-simple',337),('add-carry',212),('add-tens',1005),('add-maximum',19998),('add-zero',120),('add-both-zero',0),('subtract-simple',234),('subtract-zero-chain',125),('subtract-decompose',155),('subtract-equal',0),('subtract-zero',9999),('subtract-both-zero',0)])
@pytest.mark.parametrize('reverse',[False,True])
def test_alternative_exchange_orders_and_all_configurations(key,want,reverse):
    m=module();seed=m.scene_seed('decimal-place:v1:'+key);attempt=m.initial_attempt(seed)
    # Independently flatten each operand into hundredths through adjacent exchanges.
    pools=['a','b'] if seed['mode']=='ADD' else ['remaining']
    if reverse:pools.reverse()
    for pool in pools:
        for place in ['hundreds','tens','ones','tenths']:
            while attempt['pools'][pool][place]:attempt=apply(m,seed,attempt,'EXCHANGE',pool=pool,place=place,direction='DOWN')
        count=attempt['pools'][pool]['hundredths'] if seed['mode']=='ADD' else seed['operands'][1]['value']
        if count:attempt=apply(m,seed,attempt,'TRANSFER',source=pool,target='result' if seed['mode']=='ADD' else 'removed',place='hundredths',count=count)
    assert m.pool_value(attempt['pools']['result' if seed['mode']=='ADD' else 'remaining'])==want
    attempt['result']=want
    assert all(m.feedback(seed,attempt).values())
    attempt['result']=want+1 if want<19998 else 0
    assert m.feedback(seed,attempt)['written_correct'] is False
    assert m.feedback(seed,attempt)['model_correct'] is True
def test_rejects_corrupt_retained_submission_feedback():
    from services.studio.subjects import decimal_place_value as m
    import copy
    seed=m.scene_seed('decimal-place:v1:add-carry')
    attempt=m.initial_attempt(seed)
    attempt['last_submission']={'source_ref':seed['source_ref'],'pools':copy.deepcopy(attempt['pools']),'result':None}
    attempt['last_validation']={'structural_valid':True,'model_complete':False,'model_correct':False,'written_correct':None,'status':'UNDER_SPECIFIED','feedback_code':'PLACE_VALUE_UNDER_SPECIFIED'}
    m.validate_attempt(seed,attempt)
    attempt['last_validation']['model_complete']=True
    with pytest.raises(ValueError):m.validate_attempt(seed,attempt)
