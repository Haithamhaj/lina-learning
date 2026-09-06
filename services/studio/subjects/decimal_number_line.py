"""Activity-owned authored decimal problems and exact mathematical attempts."""
from copy import deepcopy
from dataclasses import dataclass
from dataclasses import replace
from typing import Mapping

from services.studio.subjects.contracts import ValidationResult, ValidationStatus
from services.studio.subjects.contracts import (
    AccessibilityContract, ActivityActionContract, ActivityContract, InteractionPolicy,
    PayloadValidatorContract, ReducerContract, ReducedMotionPolicy, RendererContract,
    SemanticValidationPolicy, ValidatorContract,
)

ACTIVITY_KEY = 'decimal_number_line'
ACTIVITY_VERSION = 'decimal-number-line-activity-v1'
RENDERER_KEY = 'decimal-number-line'
RENDERER_VERSION = 'decimal-number-line-renderer-v1'
PROFILE_VERSION = 'subject-profile-v3'
SEED_VERSION = 'decimal-number-line-scene-v1'
CATALOG_VERSION = 'decimal-number-line-catalog-v1'
STEPS = {'ones': 1000, 'tenths': 100, 'hundredths': 10}


def exact_value(value: object) -> int:
    if type(value) is not int or not 0 <= value <= 10000:
        raise ValueError('Expected integer thousandths in [0,10000].')
    return value


def round_value(value: int, place: str) -> int:
    exact_value(value)
    if place not in STEPS:
        raise ValueError('Unsupported rounding place.')
    step = STEPS[place]
    lower = value // step * step
    return lower + step if 2 * (value - lower) >= step else lower


@dataclass(frozen=True)
class Problem:
    key: str
    mode: str
    values: tuple[int, ...]
    texts: tuple[str, ...]
    bounds: tuple[int, int]
    place: str | None = None

    @property
    def source_ref(self) -> str:
        return f'decimal-line:v1:{self.key}'


PROBLEMS = (
    Problem('compare-less', 'COMPARE', (444, 446), ('0.444', '0.446'), (400, 500)),
    Problem('compare-equal', 'COMPARE', (500, 500), ('0.5', '0.500'), (0, 1000)),
    Problem('compare-greater', 'COMPARE', (1250, 999), ('1.250', '0.999'), (0, 2000)),
    Problem('round-below', 'ROUND', (444,), ('0.444',), (400, 500), 'hundredths'),
    Problem('round-midpoint', 'ROUND', (445,), ('0.445',), (400, 500), 'hundredths'),
    Problem('round-above', 'ROUND', (446,), ('0.446',), (400, 500), 'hundredths'),
    Problem('round-carry', 'ROUND', (999,), ('0.999',), (900, 1000), 'hundredths'),
    Problem('round-zero', 'ROUND', (0,), ('0.000',), (0, 100), 'hundredths'),
    Problem('round-exact', 'ROUND', (450,), ('0.450',), (400, 500), 'hundredths'),
    Problem('round-tenths', 'ROUND', (9950,), ('9.950',), (9000, 10000), 'tenths'),
    Problem('round-ones', 'ROUND', (9500,), ('9.500',), (9000, 10000), 'ones'),
)


def problem_for(ref: object) -> Problem:
    if not isinstance(ref, str):
        raise ValueError('Problem source must be exact.')
    for problem in PROBLEMS:
        if problem.source_ref == ref:
            return problem
    raise ValueError('Unknown authored problem source.')


def authored_problem_sources(subject_key: str | None) -> tuple[dict, ...]:
    """Prepared problems, never retrieved citations or arbitrary generated questions."""
    if subject_key != 'MATH':
        return ()
    return tuple({**scene_seed(p.source_ref), 'activity_hint': ACTIVITY_KEY} for p in PROBLEMS)


def scene_seed(ref: str) -> dict:
    p = problem_for(ref)
    ids = ('a', 'b') if p.mode == 'COMPARE' else ('x',)
    endpoints = []
    if p.mode == 'ROUND':
        step = STEPS[p.place]
        lower = p.values[0] // step * step
        endpoints = sorted({lower, lower if p.values[0] == lower else lower + step})
    return dict(source_ref=p.source_ref, catalog_version=CATALOG_VERSION, mode=p.mode,
                points=[dict(id=i, value=v, text=t) for i, v, t in zip(ids, p.values, p.texts)],
                axis_min=p.bounds[0], axis_max=p.bounds[1], grid_step=1, target_place=p.place,
                endpoints=endpoints, positions={i: None for i in ids}, selection=None)


def validate_seed(seed: Mapping) -> None:
    if dict(seed) != scene_seed(seed.get('source_ref')):
        raise ValueError('Seed differs from authored configuration.')
    # Python equality must not admit booleans/floats as exact serialized values.
    for point in seed['points']:
        exact_value(point['value'])
    exact_value(seed['axis_min']); exact_value(seed['axis_max'])
    if type(seed['grid_step']) is not int:
        raise ValueError('Grid step must be exact.')
    for value in seed['endpoints']:
        exact_value(value)


def current_state(activity_state: Mapping) -> tuple[dict, dict]:
    seed = activity_state.get('scene_seed')
    if not isinstance(seed, Mapping):
        raise ValueError('Authoritative seed required.')
    validate_seed(seed)
    current = activity_state.get(ACTIVITY_KEY, seed)
    if not isinstance(current, Mapping):
        raise ValueError('Authoritative attempt required.')
    positions = current.get('positions')
    if not isinstance(positions, Mapping) or set(positions) != set(seed['positions']):
        raise ValueError('Attempt point identities are inconsistent.')
    for value in positions.values():
        if value is not None and not seed['axis_min'] <= exact_value(value) <= seed['axis_max']:
            raise ValueError('Point outside axis.')
    selection = current.get('selection')
    choices = ('LT', 'EQ', 'GT') if seed['mode'] == 'COMPARE' else seed['endpoints']
    if selection is not None and (selection not in choices or (seed['mode'] == 'ROUND' and type(selection) is not int)):
        raise ValueError('Unsupported selection.')
    return dict(seed), dict(positions=dict(positions), selection=selection)


def context(payload: Mapping) -> tuple[Mapping, dict, dict]:
    action, state = payload.get('action'), payload.get('activity_state')
    if not isinstance(action, Mapping) or not isinstance(state, Mapping):
        raise ValueError('Authoritative action/state required.')
    seed, attempt = current_state(state)
    return action, seed, attempt


def validate_place(payload: Mapping) -> ValidationResult:
    action, seed, attempt = context(payload)
    if set(action) != {'point_id', 'from_value', 'value'} or action['point_id'] not in attempt['positions']:
        raise ValueError('Unknown point or operation shape.')
    if action['from_value'] is not None:
        exact_value(action['from_value'])
    if action['from_value'] != attempt['positions'][action['point_id']]:
        raise ValueError('Point source mismatches Snapshot.')
    if not seed['axis_min'] <= exact_value(action['value']) <= seed['axis_max']:
        raise ValueError('Point outside declared axis.')
    return ValidationResult(ValidationStatus.VALID)


def validate_select(payload: Mapping) -> ValidationResult:
    action, seed, attempt = context(payload)
    if set(action) != {'from_selection', 'selection'} or action['from_selection'] != attempt['selection']:
        raise ValueError('Selection source mismatches Snapshot.')
    current_state({'scene_seed': seed, ACTIVITY_KEY: {**attempt, 'selection': action['selection']}})
    if action['selection'] is None:
        raise ValueError('Select a declared answer.')
    return ValidationResult(ValidationStatus.VALID)


def validate_submit(payload: Mapping) -> ValidationResult:
    action, seed, attempt = context(payload)
    if set(action) != {'source_ref', 'positions', 'selection'} or action['source_ref'] != seed['source_ref']:
        raise ValueError('Submission source mismatch.')
    _, submitted = current_state({'scene_seed': seed, ACTIVITY_KEY: action})
    if submitted != attempt:
        raise ValueError('Submission mismatches Snapshot.')
    if any(v is None for v in attempt['positions'].values()) or attempt['selection'] is None:
        raise ValueError('Complete placements and selection before submission.')
    p = problem_for(seed['source_ref'])
    expected = ('LT' if p.values[0] < p.values[1] else 'GT' if p.values[0] > p.values[1] else 'EQ') if p.mode == 'COMPARE' else round_value(p.values[0], p.place)
    correct = attempt['selection'] == expected and all(attempt['positions'][point['id']] == point['value'] for point in seed['points'])
    return ValidationResult(ValidationStatus.VALID if correct else ValidationStatus.INVALID,
                            feedback_code='DECIMAL_LINE_CORRECT' if correct else 'DECIMAL_LINE_TRY_AGAIN',
                            next_action_keys=('PLACE_POINT', 'SELECT_ANSWER', 'SUBMIT_CONFIGURATION'))


ACTION_NAMES = {'PLACE_POINT': 'place', 'SELECT_ANSWER': 'select', 'SUBMIT_CONFIGURATION': 'submit'}
VALIDATORS = {'PLACE_POINT': validate_place, 'SELECT_ANSWER': validate_select, 'SUBMIT_CONFIGURATION': validate_submit}
EVENTS = {'PLACE_POINT': 'point_placed', 'SELECT_ANSWER': 'answer_selected', 'SUBMIT_CONFIGURATION': 'configuration_submitted'}
ACCESSIBILITY = AccessibilityContract(
    accessible_equivalent='Exact bounded decimal controls and named point summaries.',
    keyboard_policy='Buttons and exact numeric placement use the same semantic operations.',
    touch_policy='Pointer capture with cancellation and explicit submission.',
    direction_policy='Mathematical axis LTR independently of Arabic/English prose.',
    mobile_fallback='Sparse labelled axis plus thousandth fine adjustment.',
    safe_fallback='Keep Tutor chat available and offer Workspace reload.',
    reduced_motion_policy=ReducedMotionPolicy.NO_MOTION,
)


def payload_version(key: str) -> str:
    return f'decimal-number-line-{ACTION_NAMES[key]}-payload-v1'


def validate_action_shape(payload: Mapping, key: str) -> None:
    expected = {'PLACE_POINT': {'point_id','from_value','value'}, 'SELECT_ANSWER': {'from_selection','selection'},
                'SUBMIT_CONFIGURATION': {'source_ref','positions','selection'}}[key]
    if set(payload) != expected:
        raise ValueError('Unsupported decimal operation shape.')
    if key == 'PLACE_POINT':
        if payload['point_id'] not in ('a','b','x'):
            raise ValueError('Unknown point identity.')
        exact_value(payload['value'])
        if payload['from_value'] is not None:
            exact_value(payload['from_value'])
    elif key == 'SELECT_ANSWER':
        for name in ('from_selection', 'selection'):
            value = payload[name]
            if value is not None and value not in ('LT','EQ','GT'):
                exact_value(value)
    elif not isinstance(payload['positions'], Mapping) or not isinstance(payload['source_ref'], str):
        raise ValueError('Unsupported submission.')


def reduce_attempt(snapshot: dict, event: object) -> dict:
    if type(event.sequence) is not int or event.sequence <= snapshot['latest_event_sequence']:
        raise ValueError('Event sequence must advance.')
    key, action = event.action_key, event.payload
    if key not in VALIDATORS:
        raise ValueError('Unknown decimal operation.')
    validate_action_shape(action, key)
    state = snapshot['state_payload']
    result = VALIDATORS[key]({'action': action, 'activity_state': state})
    seed, attempt = current_state(state)
    previous = state.get(ACTIVITY_KEY, {})
    for name in ('last_submission', 'last_validation'):
        if name in previous:
            attempt[name] = deepcopy(previous[name])
    if key == 'PLACE_POINT':
        attempt['positions'][action['point_id']] = action['value']
    elif key == 'SELECT_ANSWER':
        attempt['selection'] = action['selection']
    else:
        attempt['last_submission'] = deepcopy(dict(action))
        attempt['last_validation'] = {'status': result.status.value, 'feedback_code': result.feedback_code}
    next_snapshot = deepcopy(snapshot)
    next_snapshot['latest_event_sequence'] = event.sequence
    if event.actor == 'STUDENT':
        next_snapshot['last_meaningful_student_event_id'] = event.id
    next_snapshot['state_payload'][ACTIVITY_KEY] = attempt
    return next_snapshot


def make_profile():
    from services.studio.subjects.math_make_ten import make_ten_profile
    base = make_ten_profile()
    actions = tuple(ActivityActionContract(
        action_key=key, event_kind=f'math.decimal_number_line.{EVENTS[key]}',
        event_schema_version=f'decimal-number-line-{name}-event-v1', payload_schema_version=payload_version(key),
        payload_validator_key=f'decimal-number-line-{name}-payload',
        interaction_policy=InteractionPolicy.TUTOR_TRIGGERING if key == 'SUBMIT_CONFIGURATION' else InteractionPolicy.RECORD_ONLY,
        semantic_validation_policy=SemanticValidationPolicy.REQUIRED,
        interaction_kind='MATH_DECIMAL_NUMBER_LINE_SUBMISSION' if key == 'SUBMIT_CONFIGURATION' else None,
        validator_key=f'decimal-number-line-{name}', validator_version=f'decimal-number-line-{name}-validator-v1',
    ) for key, name in ACTION_NAMES.items())
    renderer = RendererContract(RENDERER_KEY, RENDERER_VERSION, 'MATH', (ACTIVITY_KEY,), SEED_VERSION, True,
        tuple(ACTION_NAMES), tuple(a.validator_key for a in actions), 'decimal-number-line-state-v1', ACCESSIBILITY, False, False, False, 'PRODUCTION')
    activity = ActivityContract(ACTIVITY_KEY, ACTIVITY_VERSION, 'MATH', 'lina.math.decimal', RENDERER_KEY, RENDERER_VERSION,
        SEED_VERSION, 'decimal-number-line-seed', actions, 'Explicit complete attempt submission.',
        'Server-owned bounded validation; no Evidence inference.', (), 'Tutor chat stays usable.', ACCESSIBILITY,
        'decimal-number-line', 'decimal-number-line-reducer-v1', True)
    return replace(base, profile_version=PROFILE_VERSION,
        activities=base.activities + (activity,), renderers=base.renderers + (renderer,),
        validators=base.validators + tuple(ValidatorContract(a.validator_key, a.validator_version, VALIDATORS[a.action_key], True) for a in actions),
        payload_validators=base.payload_validators + (PayloadValidatorContract('decimal-number-line-seed', SEED_VERSION, validate_seed),) +
            tuple(PayloadValidatorContract(a.payload_validator_key, a.payload_schema_version, lambda p, k=a.action_key: validate_action_shape(p, k)) for a in actions),
        reducers=base.reducers + (ReducerContract('decimal-number-line', 'decimal-number-line-reducer-v1', reduce_attempt),))
