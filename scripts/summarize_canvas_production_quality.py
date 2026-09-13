"""Summarize every observed Canvas model call, including failed acceptance runs.

Token estimates use the project's configured rate card, not a billing claim.
Harness elapsed time includes Tutor turns and setup; it is not Canvas latency.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from services.model_gateway.pricing import estimate_openai_cost


def summarize(path: Path) -> dict:
    data = json.loads(path.read_text())
    records = data['records']
    calls = [r for r in records if r['kind'] == 'luna_request']
    inputs = sum(r['input_tokens'] for r in calls)
    outputs = sum(r['output_tokens'] for r in calls)
    cached = sum(r.get('cached_input_tokens', 0) or 0 for r in calls)
    phase_ms: dict[str, int] = {}
    for index, record in enumerate(records):
        if record['kind'] != 'luna_request':
            continue
        following = []
        for item in records[index+1:]:
            if item['kind'] in {'luna_request', 'request_input'}:
                break
            if item['kind'] == 'tool_arguments':
                following.append(item['name'])
        phase = 'independent_review' if record.get('phase') == 'independent_review' else '+'.join(following) or 'final_plan_or_review'
        phase_ms[phase] = phase_ms.get(phase, 0) + record['elapsed_ms']
    result_path = path.with_name(path.name.replace('-timing.json', '.json'))
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    return {'run': path.name.removesuffix('-timing.json'), 'protocol_status': result.get('status','UNKNOWN'),
        'run_id': result.get('run_id'), 'harness_elapsed_ms': data.get('elapsed_ms'),
        'model_calls': len(calls), 'luna_ms': sum(r['elapsed_ms'] for r in calls),
        'input_tokens': inputs, 'output_tokens': outputs, 'cached_input_tokens': cached,
        'estimated_token_cost_usd': estimate_openai_cost('gpt-5.6-luna', inputs, outputs,
            cached_input_tokens=cached, cache_write_tokens=0) if calls else None,
        'model_turn_phase_ms': phase_ms,
        'preview_ms': sum(r['elapsed_ms'] for r in records if r['kind']=='browser_preview'),
        'tool_argument_bytes': sum(r['bytes'] for r in records if r['kind']=='tool_arguments'),
        'system_chars': [r['system_chars'] for r in records if r['kind']=='request_input'],
        'visual_acceptance': 'SEPARATE_HUMAN_REVIEW_REQUIRED'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    args=parser.parse_args()
    rows=[summarize(path) for path in sorted(args.directory.glob('*-timing.json'))]
    output={'scope':'Observed Canvas calls only; no hosted-tool fees or Tutor costs. Failures retained. Zero observed calls is not proof of zero billed usage.',
        'rows':rows,'observed_calls':sum(r['model_calls'] for r in rows),
        'observed_token_cost_usd':round(sum(r['estimated_token_cost_usd'] or 0 for r in rows),8)}
    destination=args.directory/'measured-results.json'
    destination.write_text(json.dumps(output,ensure_ascii=False,indent=2))
    print(destination)

if __name__=='__main__':
    main()
