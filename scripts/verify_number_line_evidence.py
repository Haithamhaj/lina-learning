"""Read-only correlation of saved observed UI requests and database readbacks."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'output/number-line-implementation-20260906'


def read(name):
    return json.loads((EVIDENCE / name).read_text())


def main():
    durable = read('browser-final-readback.stdout')
    first = read('browser-phase-one-observed.json')
    second = read('browser-phase-two-observed.json')
    stale = read('browser-stale-observed.json')
    assert durable['session_id'] == first['session_id'] == second['session_id'] == stale['session_id']
    events = durable['events']
    by_key = {event['idempotency_key']: event for event in events}
    assert len(by_key) == len(events) == durable['latest_sequence'] == 36
    assert [event['sequence'] for event in events] == list(range(1, 37))
    versions = {}
    for event in events:
        assert event['base_version'] == versions.get(event['scene_id'], 0)
        assert event['resulting_version'] == event['base_version'] + 1
        versions[event['scene_id']] = event['resulting_version']
    correlations = []
    for mode in ('equality', 'midpoint', 'carry'):
        case = second[mode]
        for operation in case['operations']:
            event = by_key[operation['key']]
            assert operation['status'] == 200
            assert event['scene_id'] == case['scene_id']
            assert event['base_version'] == operation['base_version']
            assert event['action'] == operation['action']
            assert event['payload']['action'] == operation['payload']
            correlations.append({'request': operation['request_id'], 'event': event['id'], 'sequence': event['sequence']})
    for name in ('mouse', 'touch', 'retry'):
        operation = first[name]
        event = by_key[operation['idempotency_key']]
        assert operation['status'] == 200 and operation['isTrusted']
        assert event['base_version'] == operation['base_version']
        assert event['payload']['action']['value'] == operation['value']
        assert event['payload']['action']['from_value'] == operation['from_value']
        correlations.append({'request': operation['request_id'], 'event': event['id'], 'sequence': event['sequence']})
    assert first['rejected_selection']['idempotency_key'] not in by_key
    assert stale['original_request']['idempotency_key'] not in by_key
    assert stale['response']['status'] == 409 and not stale['released_request_modified']
    assert first['cancellation']['operation_requests'] == 0
    assert not first['cancellation']['truncated'] and not first['cancellation']['hasMore']
    final = second['final_current_api_submit']
    event = by_key[final['key']]
    assert event['base_version'] == final['base_version'] == 6
    assert final['status'] == final['continuation_status'] == 200
    assert not final['truncated'] and not final['hasMore']
    correlations.append({'request': final['request_id'], 'event': event['id'], 'sequence': event['sequence']})
    assert durable['rebuild_equal'] and durable['watermark'] == 36
    assert durable['scene_version'] == versions[second['carry']['scene_id']] == 7
    assert durable['state']['decimal_number_line']['positions'] == {'x': 999}
    assert durable['state']['decimal_number_line']['selection'] == 1000
    submissions = [event for event in events if event['action'] == 'SUBMIT_CONFIGURATION']
    assert len(submissions) == len(durable['interactions']) == len(durable['executions']) == 7
    assert sum(event['payload']['validation']['status'] == 'INVALID' for event in submissions) == 2
    assert all(row['status'] == 'COMPLETED' for row in durable['interactions'])
    assert {row['ai_execution_id'] for row in durable['interactions']} == {row['id'] for row in durable['executions']}
    assert all(row['success'] and row['provider'] == 'local-demo' and row['task'] == 'tutor' for row in durable['executions'])
    assert all(row['role'] == 'tutor' for row in durable['messages'])
    assert sum(row['prepared'] for row in durable['messages']) == 4
    messages = {row['id']: row for row in durable['messages']}
    assert all(messages[row['tutor_message_id']]['origin'] == 'STUDIO_INTERACTION' for row in durable['interactions'])
    before = read('browser-before-submit.stdout')
    assert before['latest_sequence'] == 4 and before['interactions'] == []
    print(json.dumps({
        'status': 'PASS', 'exact_request_key_correlations': correlations,
        'events': 36, 'submissions': 7, 'completed_interactions': 7,
        'configured_mock_executions': 7, 'student_messages': 0,
        'prepared_scenes': 4, 'rebuild_equal': True,
        'limits': second['limits'] + [second['capture_limit'], 'Other comparison operations have observed version/payload records rather than retained request keys; full durable history remains available.'],
    }, indent=2))


if __name__ == '__main__':
    main()
