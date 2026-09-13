"""Auditable diverse live acceptance using the production path and disposable owners.

This observer changes no production settings, model, source, tool result or decision.
Rendering/protocol success is recorded separately from human visual acceptance.
"""
from __future__ import annotations

import argparse
import base64
import json
from hashlib import sha256
from pathlib import Path
import runpy
import subprocess
import sys
from time import perf_counter


def observe_case(*, case: dict, env_file: Path, stem: Path, owner_run_id: str | None = None) -> None:
    from services.studio.agent import orchestrator
    from services.studio import custom_visual_preview

    root = Path(__file__).resolve().parents[1]
    sources = [root / name for name in (
        "services/studio/agent/orchestrator.py", "services/studio/agent/intelligence.py",
        "services/studio/custom_visual_preview.py", "scripts/preview_custom_visual.cjs",
        "scripts/custom_visual_state_reads.cjs", "package.json", "package-lock.json",
        "services/tutor/runtime.py", "apps/api/routes/student.py", "services/studio/interactions.py", "workers/agentic_canvas_handlers.py",
        "services/studio/full_power_canvas.py",
        "apps/web/lib/studio/custom-visual-sandbox.ts", "apps/web/lib/studio/agentic-canvas.tsx")]
    sources += sorted((root / "runtime/canvas-agent").rglob("*.md"))
    configuration = {str(path.relative_to(root)): sha256(path.read_bytes()).hexdigest() for path in sources}
    records = []
    started = perf_counter()
    timing_path = stem.with_name(stem.name + '-timing.json')

    def write_timing():
        timing_path.write_text(json.dumps({'elapsed_ms': round((perf_counter()-started)*1000), 'runtime_source_digests': configuration, 'records': records}, indent=2))

    original_hooks = orchestrator.CanvasCompositionRunHooks

    class ObservingHooks(original_hooks):
        async def on_llm_start(self, context, agent, system_prompt, input_items):
            self.request_started = perf_counter()
            records.append({'kind':'input_shape','items':[
                {'type':item.get('type'),'role':item.get('role'),'name':item.get('name'),
                 'output_kind':type(item.get('output')).__name__,
                 'output_parts':[part.get('type') for part in item.get('output',[]) if isinstance(part,dict)] if isinstance(item.get('output'),list) else [],
                 'content_parts':[part.get('type') for part in item.get('content',[]) if isinstance(part,dict)] if isinstance(item.get('content'),list) else []}
                for item in input_items if isinstance(item,dict)]})
            records.append({'kind':'request_input', 'system_chars':len(str(system_prompt)),
                'history_chars':len(json.dumps(input_items, default=str))})
            write_timing()
            await super().on_llm_start(context, agent, system_prompt, input_items)

        async def on_llm_end(self, context, agent, response):
            await super().on_llm_end(context, agent, response)
            usage = response.usage
            records.append({'kind':'luna_request', 'phase':'independent_review' if agent.name == 'Lina Canvas verification' else 'composition', 'elapsed_ms':round((perf_counter()-self.request_started)*1000),
                'input_tokens':usage.input_tokens, 'output_tokens':usage.output_tokens,
                'cached_input_tokens':getattr(usage.input_tokens_details,'cached_tokens',0)})
            for item in response.output:
                if getattr(item,'type',None) == 'message':
                    stem.with_name(stem.name+f'-final-{len(records)}.json').write_text(
                        json.dumps(item.model_dump(mode='json'),ensure_ascii=False,indent=2))
                if getattr(item,'type',None) != 'function_call':
                    continue
                records.append({'kind':'tool_arguments','name':item.name,'bytes':len(item.arguments.encode())})
                if item.name in {'create_custom_visual','refine_custom_visual'}:
                    stem.with_name(stem.name+f'-call-{len(records)}.json').write_text(item.arguments)
            write_timing()

    orchestrator.CanvasCompositionRunHooks = ObservingHooks
    original_preview = custom_visual_preview.preview_custom_visual

    def observing_preview(**kwargs):
        preview_started = perf_counter()
        try:
            result = original_preview(**kwargs)
            saved = json.loads(json.dumps(result))
            sequence = len(records)
            for index, view in enumerate(saved['views']):
                stem.with_name(stem.name+f'-preview-{sequence}-{index}.png').write_bytes(
                    base64.b64decode(view.pop('image_url').split(',')[1]))
            stem.with_name(stem.name+f'-preview-{sequence}.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2))
            return result
        finally:
            records.append({'kind':'browser_preview','elapsed_ms':round((perf_counter()-preview_started)*1000)})
            write_timing()

    custom_visual_preview.preview_custom_visual = observing_preview
    sys.argv = ['scripts.prove_studio_agentic_durable_live','--live','--env-file',str(env_file),
        '--initial-request',case['request'],'--successor-request','Keep this visual and continue in Chat.',
        '--output',str(stem.with_suffix('.json'))]
    if owner_run_id:
        sys.argv.extend(["--owner-run-id", owner_run_id])
    try:
        runpy.run_module('scripts.prove_studio_agentic_durable_live',run_name='__main__')
    finally:
        write_timing()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', required=True)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--cases', type=Path, default=Path('tests/fixtures/canvas_production_cases.json'))
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--label', default='acceptance')
    parser.add_argument('--owner-run-id', help='Existing verified disposable owner for registry lifecycle proof')
    parser.add_argument('--case-id', help='Run one case as an isolated observer process')
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.case_id:
        case = next(case for case in cases if case['id']==args.case_id)
        observe_case(case=case,env_file=args.env_file,stem=args.output_dir/f'{args.label}-{case["id"]}', owner_run_id=args.owner_run_id)
        return
    outcomes = []
    for case in cases:
        stem = args.output_dir/f'{args.label}-{case["id"]}'
        with stem.with_suffix('.log').open('w') as log:
            result = subprocess.run([sys.executable,'-m','scripts.prove_canvas_production_quality',
                '--live','--env-file',str(args.env_file),'--cases',str(args.cases),
                '--output-dir',str(args.output_dir),'--label',args.label,'--case-id',case['id'],
                *(['--owner-run-id',args.owner_run_id] if args.owner_run_id else [])],stdout=log,stderr=subprocess.STDOUT)
        outcomes.append({'case_id':case['id'],'protocol_exit_code':result.returncode,'visual_acceptance':'REQUIRES_REVIEW'})
        (args.output_dir/f'{args.label}-outcomes.json').write_text(json.dumps(outcomes,indent=2))
        print(case['id'],result.returncode,flush=True)
    if any(item['protocol_exit_code'] for item in outcomes):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
