"""Bounded authored decimal ADD/SUBTRACT with conserved aggregate pools."""
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import re

ACTIVITY_KEY = 'decimal_place_value'
PROFILE_VERSION = 'subject-profile-v4'
ACTIVITY_VERSION = 'decimal-place-value-activity-v1'
RENDERER_KEY = 'decimal-place-value'
RENDERER_VERSION = 'decimal-place-value-renderer-v1'
SEED_VERSION = 'decimal-place-value-scene-v1'
CATALOG_VERSION = 'decimal-place-value-catalog-v1'
PLACES = {'hundreds': 10000, 'tens': 1000, 'ones': 100, 'tenths': 10, 'hundredths': 1}
MAX_VALUE = 19998


def integer(value, maximum=MAX_VALUE):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('Expected bounded nonnegative integer hundredths/count.')
    return value


def parse_result(text):
    if not isinstance(text, str) or len(text) > 6:
        raise ValueError('Expected bounded decimal text.')
    normalized = text.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٫', '01234567890123456789.'))
    if re.fullmatch(r'(?:0|[1-9][0-9]{0,2})(?:\.[0-9]{1,2})?', normalized) is None:
        raise ValueError('Expected decimal with at most two fractional digits.')
    whole, _, fraction = normalized.partition('.')
    return integer(int(whole) * 100 + int(fraction.ljust(2, '0')))


@dataclass(frozen=True)
class Problem:
    key: str
    mode: str
    a: int
    b: int
    texts: tuple[str, str]

    @property
    def source_ref(self):
        return 'decimal-place:v1:' + self.key


PROBLEMS = (
    Problem('add-simple', 'ADD', 123, 214, ('1.23', '2.14')),
    Problem('add-carry', 'ADD', 127, 85, ('1.27', '0.85')),
    Problem('add-tens', 'ADD', 995, 10, ('9.95', '0.10')),
    Problem('add-maximum', 'ADD', 9999, 9999, ('99.99', '99.99')),
    Problem('add-zero', 'ADD', 0, 120, ('0', '1.20')),
    Problem('add-both-zero', 'ADD', 0, 0, ('0.0', '0.00')),
    Problem('subtract-simple', 'SUBTRACT', 357, 123, ('3.57', '1.23')),
    Problem('subtract-zero-chain', 'SUBTRACT', 200, 75, ('2.00', '0.75')),
    Problem('subtract-decompose', 'SUBTRACT', 230, 75, ('2.30', '0.75')),
    Problem('subtract-equal', 'SUBTRACT', 120, 120, ('1.2', '1.20')),
    Problem('subtract-zero', 'SUBTRACT', 9999, 0, ('99.99', '0')),
    Problem('subtract-both-zero', 'SUBTRACT', 0, 0, ('0', '0.00')),
)


def problem_for(ref):
    if not isinstance(ref, str):
        raise ValueError('Exact authored reference required.')
    for problem in PROBLEMS:
        if problem.source_ref == ref:
            return problem
    raise ValueError('Unknown authored decimal configuration.')


def counts(value):
    integer(value)
    result = {}
    for place, weight in PLACES.items():
        result[place], value = divmod(value, weight)
    return result


def scene_seed(ref):
    p = problem_for(ref)
    return dict(source_ref=p.source_ref, catalog_version=CATALOG_VERSION,
                mode=p.mode, operands=[dict(id='a', value=p.a, text=p.texts[0]), dict(id='b', value=p.b, text=p.texts[1])],
                places=[dict(id=k, weight=v) for k, v in PLACES.items()],
                pools=({'a': counts(p.a), 'b': counts(p.b), 'result': counts(0)} if p.mode == 'ADD'
                       else {'remaining': counts(p.a), 'removed': counts(0)}), result=None)


def authored_problem_sources(subject_key):
    return tuple({**scene_seed(p.source_ref), 'activity_hint': ACTIVITY_KEY} for p in PROBLEMS) if subject_key == 'MATH' else ()


def validate_seed(seed):
    # Exact recursive serialization comparison rejects numeric booleans/floats.
    import json
    if not isinstance(seed, Mapping) or json.dumps(dict(seed), sort_keys=True) != json.dumps(scene_seed(seed.get('source_ref')), sort_keys=True):
        raise ValueError('Seed differs from authored configuration.')


def initial_attempt(seed):
    validate_seed(seed)
    return dict(pools=deepcopy(seed['pools']), result=None)


def pool_value(pool):
    if not isinstance(pool, Mapping) or set(pool) != set(PLACES):
        raise ValueError('Unknown or missing place.')
    return sum(integer(pool[k]) * weight for k, weight in PLACES.items())


def validate_attempt(seed, attempt):
    validate_seed(seed)
    if not isinstance(attempt, Mapping) or not {'pools', 'result'} <= set(attempt) or set(attempt) - {'pools', 'result', 'last_submission', 'last_validation'}:
        raise ValueError('Malformed attempt.')
    pools = attempt['pools']
    if not isinstance(pools, Mapping) or set(pools) != set(seed['pools']):
        raise ValueError('Unknown or missing pool.')
    values = {key: pool_value(pool) for key, pool in pools.items()}
    p = problem_for(seed['source_ref'])
    total = p.a + p.b if p.mode == 'ADD' else p.a
    if sum(values.values()) != total:
        raise ValueError('Quantity conservation violated.')
    if p.mode == 'SUBTRACT' and values['removed'] > p.b:
        raise ValueError('Over-removal is not permitted.')
    if attempt['result'] is not None:
        integer(attempt['result'])
    if ('last_submission' in attempt) != ('last_validation' in attempt):
        raise ValueError('Submission and validation must be paired.')
    if 'last_submission' in attempt:
        submission=attempt['last_submission']
        if not isinstance(submission,Mapping) or set(submission)!={'source_ref','pools','result'} or submission['source_ref']!=seed['source_ref']:
            raise ValueError('Malformed retained submission.')
        f=feedback(seed,dict(pools=submission['pools'],result=submission['result']))
        status='UNDER_SPECIFIED' if not f['model_complete'] or f['written_correct'] is None else ('VALID' if f['written_correct'] else 'INVALID')
        expected={**f,'status':status,'feedback_code':'PLACE_VALUE_'+status}
        import json
        if json.dumps(attempt['last_validation'],sort_keys=True)!=json.dumps(expected,sort_keys=True):
            raise ValueError('Retained validation differs from submitted state.')


def feedback(seed, attempt):
    validate_attempt(seed, attempt)
    p = problem_for(seed['source_ref'])
    complete = (pool_value(attempt['pools']['a']) == pool_value(attempt['pools']['b']) == 0 if p.mode == 'ADD'
                else pool_value(attempt['pools']['removed']) == p.b)
    expected = p.a + p.b if p.mode == 'ADD' else p.a - p.b
    actual = pool_value(attempt['pools']['result' if p.mode == 'ADD' else 'remaining'])
    return dict(structural_valid=True, model_complete=complete, model_correct=complete and actual == expected,
                written_correct=None if attempt['result'] is None else attempt['result'] == expected)


def transition(seed, attempt, key, action):
    validate_attempt(seed, attempt)
    result = deepcopy(dict(attempt))
    if key in ('EXCHANGE', 'TRANSFER'):
        if not isinstance(action.get('from_pools'), Mapping):
            raise ValueError('Prior pool state required.')
        validate_attempt(seed, dict(pools=action['from_pools'], result=attempt['result']))
        if action['from_pools'] != attempt['pools']:
            raise ValueError('Pool state mismatches Snapshot.')
    if key == 'EXCHANGE':
        if set(action) != {'from_pools','pool','place','direction'} or action['pool'] not in result['pools'] or action['place'] not in PLACES:
            raise ValueError('Unknown exchange.')
        places=list(PLACES); index=places.index(action['place']); pool=result['pools'][action['pool']]
        if action['direction']=='DOWN' and index < len(places)-1:
            pool[places[index]]-=1;pool[places[index+1]]+=10
        elif action['direction']=='UP' and index > 0:
            pool[places[index]]-=10;pool[places[index-1]]+=1
        else:
            raise ValueError('Exchange requires adjacent supported place.')
    elif key == 'TRANSFER':
        if set(action) != {'from_pools','source','target','place','count'}:
            raise ValueError('Malformed transfer.')
        pair=(action['source'],action['target'])
        allowed=(('a','result'),('b','result')) if seed['mode']=='ADD' else (('remaining','removed'),('removed','remaining'))
        if pair not in allowed or action['place'] not in PLACES or integer(action['count']) == 0:
            raise ValueError('Unsupported transfer.')
        result['pools'][pair[0]][action['place']]-=action['count']
        result['pools'][pair[1]][action['place']]+=action['count']
    elif key == 'SET_RESULT':
        if set(action) != {'from_result','result'}:
            raise ValueError('Malformed result edit.')
        if action['from_result'] is not None:
            integer(action['from_result'])
        if action['from_result'] != attempt['result']:
            raise ValueError('Result mismatches Snapshot.')
        result['result']=action['result']
    elif key == 'SUBMIT_CONFIGURATION':
        if set(action) != {'source_ref','pools','result'} or action['source_ref']!=seed['source_ref']:
            raise ValueError('Submission source mismatch.')
        validate_attempt(seed, dict(pools=action['pools'], result=action['result']))
        if action['pools']!=attempt['pools'] or action['result']!=attempt['result']:
            raise ValueError('Submission mismatches Snapshot.')
    else:
        raise ValueError('Unknown action.')
    validate_attempt(seed,result)
    return result


ACTION_NAMES = {'EXCHANGE':'exchange','TRANSFER':'transfer','SET_RESULT':'result','SUBMIT_CONFIGURATION':'submit'}


def payload_version(key):
    return f'decimal-place-value-{ACTION_NAMES[key]}-payload-v1'


def current_state(state):
    seed=state.get('scene_seed')
    validate_seed(seed)
    attempt=state.get(ACTIVITY_KEY,initial_attempt(seed))
    validate_attempt(seed,attempt)
    return seed,deepcopy(dict(attempt))


def validate_action_shape(action,key):
    shapes={'EXCHANGE':{'from_pools','pool','place','direction'},'TRANSFER':{'from_pools','source','target','place','count'},
            'SET_RESULT':{'from_result','result'},'SUBMIT_CONFIGURATION':{'source_ref','pools','result'}}
    if not isinstance(action,Mapping) or set(action)!=shapes[key]:
        raise ValueError('Malformed place-value action.')
    if key in ('EXCHANGE','TRANSFER'):
        if not isinstance(action['from_pools'],Mapping) or not 2<=len(action['from_pools'])<=3:
            raise ValueError('Bounded prior pools required.')
        for pool in action['from_pools'].values():pool_value(pool)
        for name in (('pool','place','direction') if key=='EXCHANGE' else ('source','target','place')):
            if not isinstance(action[name],str):raise ValueError('Typed identifier required.')
        if key=='TRANSFER':integer(action['count'])
    elif key=='SET_RESULT':
        for name in ('from_result','result'):
            if action[name] is not None:integer(action[name])
    else:
        if not isinstance(action['source_ref'],str) or not isinstance(action['pools'],Mapping):raise ValueError('Typed submission required.')
        for pool in action['pools'].values():pool_value(pool)
        if action['result'] is not None:integer(action['result'])


def validate_action(payload,key):
    from services.studio.subjects.contracts import ValidationResult,ValidationStatus
    action=payload.get('action');state=payload.get('activity_state')
    validate_action_shape(action,key)
    if not isinstance(state,Mapping):raise ValueError('Authoritative state required.')
    seed,attempt=current_state(state)
    transition(seed,attempt,key,action)
    if key!='SUBMIT_CONFIGURATION':return ValidationResult(ValidationStatus.VALID)
    f=feedback(seed,attempt)
    status=ValidationStatus.VALID if all(f.values()) else (ValidationStatus.UNDER_SPECIFIED if not f['model_complete'] or f['written_correct'] is None else ValidationStatus.INVALID)
    return ValidationResult(status,feedback_code='PLACE_VALUE_'+status.value,next_action_keys=tuple(ACTION_NAMES))


def reduce_attempt(snapshot,event):
    if type(event.sequence) is not int or event.sequence<=snapshot['latest_event_sequence']:raise ValueError('Sequence must advance.')
    seed,attempt=current_state(snapshot['state_payload'])
    validation=validate_action({'action':event.payload,'activity_state':snapshot['state_payload']},event.action_key)
    attempt=transition(seed,attempt,event.action_key,event.payload)
    if event.action_key=='SUBMIT_CONFIGURATION':
        submitted_feedback=feedback(seed,attempt)
        attempt['last_submission']=deepcopy(dict(event.payload))
        attempt['last_validation']={**submitted_feedback,'status':validation.status.value,'feedback_code':validation.feedback_code}
    result=deepcopy(snapshot);result['latest_event_sequence']=event.sequence
    if event.actor=='STUDENT':result['last_meaningful_student_event_id']=event.id
    result['state_payload'][ACTIVITY_KEY]=attempt
    return result


def make_profile():
    from dataclasses import replace
    from services.studio.subjects.decimal_number_line import make_profile as base_profile
    from services.studio.subjects.contracts import (AccessibilityContract,ActivityActionContract,ActivityContract,
        InteractionPolicy,PayloadValidatorContract,ReducerContract,ReducedMotionPolicy,RendererContract,
        SemanticValidationPolicy,ValidatorContract)
    base=base_profile()
    accessibility=AccessibilityContract('Named place columns and aggregate quantities.','All exchanges and transfers have buttons.',
        'Captured pointer drag to declared targets; cancellation is record-free.','Mathematical columns LTR; surrounding English/Arabic.',
        'Compact place table with accessible controls.','Reload workspace; Tutor remains usable.',ReducedMotionPolicy.NO_MOTION)
    actions=tuple(ActivityActionContract(action_key=key,event_kind=f'math.decimal_place_value.{name}',
        event_schema_version=f'decimal-place-value-{name}-event-v1',payload_schema_version=payload_version(key),
        payload_validator_key=f'decimal-place-value-{name}-payload',
        interaction_policy=InteractionPolicy.TUTOR_TRIGGERING if key=='SUBMIT_CONFIGURATION' else InteractionPolicy.RECORD_ONLY,
        semantic_validation_policy=SemanticValidationPolicy.REQUIRED,
        interaction_kind='MATH_DECIMAL_PLACE_VALUE_SUBMISSION' if key=='SUBMIT_CONFIGURATION' else None,
        validator_key=f'decimal-place-value-{name}',validator_version=f'decimal-place-value-{name}-validator-v1') for key,name in ACTION_NAMES.items())
    renderer=RendererContract(RENDERER_KEY,RENDERER_VERSION,'MATH',(ACTIVITY_KEY,),SEED_VERSION,True,tuple(ACTION_NAMES),
        tuple(a.validator_key for a in actions),'decimal-place-value-state-v1',accessibility,False,False,False,'PRODUCTION')
    activity=ActivityContract(ACTIVITY_KEY,ACTIVITY_VERSION,'MATH','lina.math.decimal',RENDERER_KEY,RENDERER_VERSION,SEED_VERSION,
        'decimal-place-value-seed',actions,'Explicit submission, including incomplete attempts.','Conservation and independent model/result feedback.',
        (),'Tutor remains usable.',accessibility,'decimal-place-value','decimal-place-value-reducer-v1',True)
    return replace(base,profile_version=PROFILE_VERSION,activities=base.activities+(activity,),renderers=base.renderers+(renderer,),
        validators=base.validators+tuple(ValidatorContract(a.validator_key,a.validator_version,lambda p,k=a.action_key:validate_action(p,k),True) for a in actions),
        payload_validators=base.payload_validators+(PayloadValidatorContract('decimal-place-value-seed',SEED_VERSION,validate_seed),)+tuple(
            PayloadValidatorContract(a.payload_validator_key,a.payload_schema_version,lambda p,k=a.action_key:validate_action_shape(p,k)) for a in actions),
        reducers=base.reducers+(ReducerContract('decimal-place-value','decimal-place-value-reducer-v1',reduce_attempt),))
