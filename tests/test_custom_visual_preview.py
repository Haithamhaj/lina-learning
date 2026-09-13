"""The real browser preview is bounded and cannot silently become syntax-only acceptance."""
import subprocess
import pytest
from services.studio import custom_visual_preview as preview


def test_preview_timeout_is_a_blocking_technical_failure(monkeypatch):
    killed = []
    class Process:
        pid = 12345
        def communicate(self, data, timeout):
            import json
            assert json.loads(data)["widths"] == [960, 640]
            assert timeout == 25
            raise subprocess.TimeoutExpired('node', timeout)
        def wait(self): pass
    monkeypatch.setattr(preview.subprocess, 'Popen', lambda *args, **kwargs: Process())
    monkeypatch.setattr(preview.os, 'killpg', lambda pid, signal: killed.append(pid))
    with pytest.raises(ValueError, match='PREVIEW_UNAVAILABLE'):
        preview.preview_custom_visual(source='window.mount=()=>{}', parameters={})
    assert killed == [12345]



def test_create_returns_real_preview_to_same_agent_and_bounds_refinement(monkeypatch):
    from agents import RunContextWrapper, ToolOutputImage
    from services.studio.agent import orchestrator as o
    from services.studio.agent.registry import CanvasBlockRegistry
    from test_full_power_canvas import _manifest
    manifest=_manifest()
    context=RunContextWrapper(o.CanvasAgentRunContext(registry=CanvasBlockRegistry(),brief_objective='Compare fractions'))
    monkeypatch.setattr(preview,'preview_custom_visual',lambda **kwargs:{'status':'RENDERED','views':[{'width':w,'text':'fraction','image_url':'data:image/png;base64,cHJldmlldw=='} for w in [960,390]]})
    args=dict(meaning='Compare fractions',label='Fractions',source='window.mount=(root)=>{root.textContent="fraction";}',entities=manifest['entities'],relations=manifest['relations'],quantities=manifest['quantities'],interactions=manifest['interactions'],presentation_steps=[],visual_descriptions=['fraction'],state_fields=[],parameters=[],parent_version_id=None,generalized_change=None)
    output=o._create_custom_visual_strict(context,block_id='first',**args)
    assert len([i for i in output if isinstance(i,ToolOutputImage)])==2
    assert o._produced_block_ids(output)==('first',)
    assert o._refine_custom_visual_enabled(context,None)
    o._refine_custom_visual(context,edits=[o.CustomVisualSourceEditV1(before=args['source'],after=args['source']+';window.rendered=true;')])
    assert o._custom_visual_tool_enabled(context,None)
    refined_id = context.context.current_custom_candidate_block_id
    assert refined_id != 'first'
    assert context.context.superseded_candidate_ids == {'first'}
    from services.studio.agentic_canvas import AgenticCanvasPlanV1
    from services.studio.agent.registry import PlanCompositionInconsistencyError
    plan = AgenticCanvasPlanV1(version='agentic-canvas-plan-v1', objective='Compare', subject_key='MATH',
        layout='FOCUS', palette='COOL', motion='NONE', reveal_order=[], placements=[
            dict(block_id='first',role='PRIMARY',order=0,span='FULL'),
            dict(block_id=refined_id,role='SUPPORT',order=1,span='FULL')])
    with pytest.raises(PlanCompositionInconsistencyError, match='superseded'):
        context.context.registry.materialize_plan(plan,current_custom_candidate_block_id=refined_id,excluded_block_ids=context.context.superseded_candidate_ids)



def test_failed_preview_has_an_explicit_diagnostic(monkeypatch):
    from services.studio.agent.orchestrator import _custom_visual_error_payload
    assert _custom_visual_error_payload(ValueError('CUSTOM_VISUAL_PREVIEW_FAILED'))['code']=='CUSTOM_VISUAL_PREVIEW_FAILED'


def test_control_outside_viewport_requires_correction_before_finalization(monkeypatch):
    from agents import RunContextWrapper
    from services.studio.agent import orchestrator as o
    from services.studio.agent.registry import CanvasBlockRegistry
    context=RunContextWrapper(o.CanvasAgentRunContext(registry=CanvasBlockRegistry()))
    def mocked(findings):
        return lambda **kwargs:{'views':[{'width':390,'text':'visual','findings':findings,'image_url':'data:image/png;base64,cHJldmlldw=='}]}
    monkeypatch.setattr(preview,'preview_custom_visual',mocked(['control below viewport']))
    o._preview_created_visual(context,{'block_id':'first'},'source',{},'first')
    assert not context.context.custom_preview_valid
    monkeypatch.setattr(preview,'preview_custom_visual',mocked([]))
    o._preview_created_visual(context,{'block_id':'corrected'},'source',{},'corrected')
    assert context.context.custom_preview_valid
    assert context.context.custom_preview_count == 2


def test_automatic_source_edits_preserve_unaffected_source_and_reject_ambiguous_targets():
    from services.studio.agent.orchestrator import _apply_source_edits, CustomVisualSourceEditV1
    original = 'window.mount=()=>{let amount=0; render(amount);};'
    assert _apply_source_edits(original, [CustomVisualSourceEditV1(before='amount=0', after='amount=1')]) == original.replace('amount=0', 'amount=1')
    for before in ['amount', 'missing']:
        with pytest.raises(ValueError, match='exactly one'):
            _apply_source_edits(original, [CustomVisualSourceEditV1(before=before, after='x')])
    with pytest.raises(ValueError, match='one to eight'):
        _apply_source_edits(original, [])


def test_mount_failure_allows_one_bounded_replacement_but_never_acceptance(monkeypatch):
    from agents import RunContextWrapper
    from services.studio.agent import orchestrator as o
    from services.studio.agent.registry import CanvasBlockRegistry
    from test_full_power_canvas import _manifest
    manifest = _manifest()
    context = RunContextWrapper(o.CanvasAgentRunContext(registry=CanvasBlockRegistry(),brief_objective='Compare portions'))
    monkeypatch.setattr(preview, 'preview_custom_visual', lambda **kwargs: {'status':'FAILED','views':[
        {'width':width,'text':'','findings':['Mount failed: invalid data shape'],'image_url':'data:image/png;base64,cHJldmlldw=='} for width in [960,390]]})
    o._create_custom_visual_strict(context,block_id='candidate',meaning='Compare portions',label='Portions',
        source='window.mount=()=>{throw new Error("invalid data shape")};',
        entities=manifest['entities'],relations=manifest['relations'],quantities=manifest['quantities'],
        interactions=manifest['interactions'],presentation_steps=[],visual_descriptions=['portions'],
        state_fields=[],parameters=[],parent_version_id=None,generalized_change=None)
    assert context.context.current_custom_candidate_block_id == 'candidate'
    assert context.context.custom_preview_valid is False
    assert o._refine_custom_visual_enabled(context, None)
    assert o._custom_visual_tool_enabled(context, None)
    context.context.custom_create_attempts = 2
    assert not o._custom_visual_tool_enabled(context, None)


def test_create_contract_retry_keeps_two_bounded_source_corrections(monkeypatch):
    from agents import RunContextWrapper
    from services.studio.agent import orchestrator as o
    from services.studio.agent.registry import CanvasBlockRegistry
    from test_full_power_canvas import _manifest
    context = RunContextWrapper(o.CanvasAgentRunContext(registry=CanvasBlockRegistry(),brief_objective='Compare portions'))
    o._custom_visual_tool_error(context,ValueError('Visual parameter value does not match its declared scalar type.'))
    manifest = _manifest()
    monkeypatch.setattr(preview,'preview_custom_visual',lambda **kwargs:{'status':'RENDERED','views':[
        {'width':w,'text':'portion','image_url':'data:image/png;base64,cHJldmlldw=='} for w in [960,320]]})
    source = 'window.mount=(root)=>{root.textContent="portion";};'
    o._create_custom_visual_strict(context,block_id='candidate-'+'a'*48,meaning='Portions',label='Portions',source=source,
        entities=manifest['entities'],relations=manifest['relations'],quantities=manifest['quantities'],interactions=manifest['interactions'],
        presentation_steps=[],visual_descriptions=['portions'],state_fields=[],parameters=[],parent_version_id=None,generalized_change=None)
    ids = [context.context.current_custom_candidate_block_id]
    for n in [1,2]:
        assert o._refine_custom_visual_enabled(context,None)
        updated = source + f';window.revision={n};'
        o._refine_custom_visual(context,edits=[o.CustomVisualSourceEditV1(before=source,after=updated)])
        source = updated
        ids.append(context.context.current_custom_candidate_block_id)
    assert len(set(ids)) == 3
    assert all(len(value)<=64 for value in ids)
    assert context.context.custom_attempt_count == 4
    assert context.context.custom_create_attempts == context.context.custom_refinement_attempts == 2
    assert not o._refine_custom_visual_enabled(context,None)
    assert not o._custom_visual_tool_enabled(context,None)
    assert context.context.superseded_candidate_ids == set(ids[:-1])


def test_repeated_replay_text_is_compact_without_hiding_failed_action_evidence():
    import json
    from services.studio.agent.orchestrator import _preview_check_summary
    passed = dict(width=320, action='STEP_REPLAY', trigger_action='SET_VALUE', semantic_id='amount', status='MATCHED', before_reload_text='quantity '*200, after_reload_text='quantity '*200)
    failed = {**passed, 'status':'FAILED', 'before_reload_text':'prefix '*100+'amount 2', 'after_reload_text':'prefix '*100+'amount 0'}
    summary = _preview_check_summary([passed]*60+[failed]*4)
    assert len(summary) == 2
    assert summary[0]['count'] == 60
    assert summary[1]['count'] == 4
    assert 'amount 2' in summary[1]['before_difference']
    assert 'amount 0' in summary[1]['after_difference']
    assert len(json.dumps(summary)) < 1000


def _review_candidate(monkeypatch):
    from agents import RunContextWrapper
    from services.studio.agent import orchestrator as o
    from services.studio.agent.registry import CanvasBlockRegistry
    from test_full_power_canvas import _manifest
    manifest = _manifest()
    context = o.CanvasAgentRunContext(registry=CanvasBlockRegistry(), brief_objective='Compare portions')
    monkeypatch.setattr(preview, 'preview_custom_visual', lambda **kwargs: {'status':'RENDERED','views':[
        {'width':w,'phase':'initial','text':'portion','image_url':'data:image/png;base64,cHJldmlldw=='} for w in [960,320]]})
    o._create_custom_visual_strict(RunContextWrapper(context),block_id='candidate',meaning='Portions',label='Portions',
        source='window.mount=root=>{root.textContent="portion";};',
        entities=manifest['entities'],relations=manifest['relations'],quantities=manifest['quantities'],interactions=manifest['interactions'],
        presentation_steps=[],visual_descriptions=['portions'],state_fields=[],parameters=[],parent_version_id=None,generalized_change=None)
    return o, context


def _review(o, block_id, accepted=True):
    return o.CanvasVisualReviewV1(block_id=block_id,educational_correctness=accepted,semantic_integrity=True,
        representation_adequacy=True,interaction_and_feedback=True,responsive_legibility=True,state_replay=True,
        visual_hierarchy_and_text_economy=True,evidence='The current candidate was inspected.',
        unresolved_defects=[] if accepted else ['Feedback contradicts the requested relationship.'])


def test_unused_replacement_slot_can_repair_source_without_increasing_total_budget(monkeypatch):
    from agents import RunContextWrapper
    o, context = _review_candidate(monkeypatch)
    wrapped = RunContextWrapper(context)
    for number in range(3):
        assert o._refine_custom_visual_enabled(wrapped,None)
        o._refine_custom_visual(wrapped,edits=[o.CustomVisualSourceEditV1(before='portion',after=f'portion{number}')])
    assert context.custom_create_attempts==1
    assert context.custom_refinement_attempts==3
    assert context.custom_attempt_count==4
    assert not o._refine_custom_visual_enabled(wrapped,None)
    assert not o._custom_visual_tool_enabled(wrapped,None)
    with pytest.raises(ValueError,match='budget exhausted'):
        o._refine_custom_visual(wrapped,edits=[o.CustomVisualSourceEditV1(before='portion',after='extra')])


def test_independent_review_uses_fresh_context_and_bounded_production_refinement(monkeypatch):
    import asyncio, json
    from types import SimpleNamespace
    from agents import RunContextWrapper
    o, context = _review_candidate(monkeypatch)
    class Agent:
        name='composer'
        def clone(self, **kwargs): return SimpleNamespace(**{'name':self.name, **kwargs})
    class Payload:
        def model_dump(self, **kwargs): return {'objective':'Compare portions'}
    calls=[]
    async def run(agent, **kwargs):
        calls.append((agent,kwargs))
        context.model_turns.append({})
        if agent.name == 'Lina Canvas verification':
            data=json.loads(kwargs['input'][0]['content'][0]['text'])
            assert 'independent_review_defects' not in data
            assert 'visual_review' not in data
            assert 'source' not in data['package']
            assert kwargs['input'][0]['content'][1]['text'].startswith('Untrusted current JavaScript source (verbatim):\nwindow.mount')
            assert len([part for part in kwargs['input'][0]['content'] if part['type']=='input_image'])==2
            assert agent.tools == [] and kwargs['max_turns']==1
            return SimpleNamespace(final_output=_review(o,context.current_custom_candidate_block_id,accepted=len(calls)>1))
        assert 'independent_review_defects' in json.loads(kwargs['input'][0]['content'][0]['text'])
        o._refine_custom_visual(RunContextWrapper(context),edits=[o.CustomVisualSourceEditV1(before='"portion"',after='"corrected portion"')])
        return SimpleNamespace(final_output=SimpleNamespace(visual_review=_review(o,context.current_custom_candidate_block_id)))
    monkeypatch.setattr(o.Runner,'run',run)
    result, attempts=asyncio.run(o._verify_and_correct_candidate(agent=Agent(),context=context,
        result=SimpleNamespace(final_output=SimpleNamespace(visual_review=_review(o,'candidate'))),
        brief=Payload(),learner_context=Payload(),trace_id='trace-proof'))
    assert context.custom_preview_valid
    assert context.custom_create_attempts == context.custom_refinement_attempts == 1
    assert len(attempts)==4 and len(calls)==3
    assert result.final_output.visual_review.block_id == context.current_custom_candidate_block_id
    assert context.superseded_candidate_ids == {'candidate'}


def test_candidate_source_keeps_real_newlines_distinct_from_literal_escapes():
    import json
    from types import SimpleNamespace
    from services.studio.agent import orchestrator as o
    source = 'window.mount = root => {\n  root.textContent = "literal \\n";\n};'
    package = SimpleNamespace(model_dump=lambda **kwargs: {'source':source,'manifest':{'version':'test'}})
    candidate = SimpleNamespace(block_id='candidate',package=package,parameters={})
    context = SimpleNamespace(registry=SimpleNamespace(blocks=lambda:[candidate]),
        current_custom_candidate_block_id='candidate',current_preview_findings=[],current_preview_views=[])
    payload = SimpleNamespace(model_dump=lambda **kwargs:{})
    content = o._current_candidate_review_input(context,payload,payload)[0]['content']
    assert 'source' not in json.loads(content[0]['text'])['package']
    assert content[1]['text'].split('\n',1)[1] == source

    context.current_preview_findings=['Canonical state ID mismatch.']
    correction=SimpleNamespace(unresolved_defects=['Feedback is stale.'],model_dump=lambda **kwargs:{'unresolved_defects':['Feedback is stale.']})
    corrected=o._current_candidate_review_input(context,payload,payload,correction=correction)[0]['content']
    instructions=json.loads(corrected[0]['text'])
    assert instructions['required_repairs']==['Canonical state ID mismatch.','Feedback is stale.']
    assert list(instructions)[:2]==['instruction','required_repairs']
    assert corrected[1]['text'].split('\n',1)[1]==source


@pytest.mark.parametrize('wrong_id', [False, True])
def test_independent_veto_cannot_reopen_exhausted_authoring_or_accept_wrong_candidate(monkeypatch, wrong_id):
    import asyncio
    from types import SimpleNamespace
    o, context = _review_candidate(monkeypatch)
    context.custom_create_attempts=context.custom_refinement_attempts=2
    context.custom_attempt_count=4
    class Agent:
        def clone(self, **kwargs): return SimpleNamespace(**kwargs)
    class Payload:
        def model_dump(self, **kwargs): return {}
    calls=[]
    async def run(agent, **kwargs):
        calls.append(agent)
        return SimpleNamespace(final_output=_review(o,'other-candidate' if wrong_id else 'candidate',accepted=wrong_id))
    monkeypatch.setattr(o.Runner,'run',run)
    _,attempts=asyncio.run(o._verify_and_correct_candidate(agent=Agent(),context=context,
        result=SimpleNamespace(final_output=SimpleNamespace(visual_review=_review(o,'candidate'))),
        brief=Payload(),learner_context=Payload(),trace_id='trace-proof'))
    assert not context.custom_preview_valid
    assert len(calls)==1 and len(attempts)==2
    assert context.custom_attempt_count==4


@pytest.mark.parametrize('used_turns', [15, 16])
def test_independent_review_respects_shared_turn_budget(monkeypatch, used_turns):
    import asyncio
    from types import SimpleNamespace
    o, context = _review_candidate(monkeypatch)
    context.model_turns = [{} for _ in range(used_turns)]
    class Agent:
        def clone(self, **kwargs): return SimpleNamespace(**kwargs)
    class Payload:
        def model_dump(self, **kwargs): return {}
    calls = []
    async def run(agent, **kwargs):
        calls.append(agent)
        context.model_turns.append({})
        return SimpleNamespace(final_output=_review(o, 'candidate', accepted=False))
    monkeypatch.setattr(o.Runner, 'run', run)
    asyncio.run(o._verify_and_correct_candidate(agent=Agent(), context=context,
        result=SimpleNamespace(final_output=SimpleNamespace(visual_review=_review(o, 'candidate'))),
        brief=Payload(), learner_context=Payload(), trace_id='trace-proof'))
    assert not context.custom_preview_valid
    assert len(context.model_turns) == 16
    assert len(calls) == 16 - used_turns
    assert context.custom_attempt_count == 1


def test_static_const_read_diagnostic_rejects_unregistered_state(monkeypatch):
    import json
    from test_full_power_canvas import _manifest
    from services.studio.full_power_canvas import CanvasSemanticManifestV1
    class Process:
        pid = 12345
        returncode = 0
        def communicate(self, data, timeout):
            return json.dumps({'status':'RENDERED', 'views':[{'width':w,'findings':[]} for w in [960,640]],
                'state_reads':[{'semantic_id':'fraction-a','line':1},{'semantic_id':'vertexA','line':2}], 'checks':[]}), ''
        def wait(self): pass
    monkeypatch.setattr(preview.subprocess, 'Popen', lambda *args, **kwargs: Process())
    monkeypatch.setattr(preview.os, 'killpg', lambda *args: None)
    result=preview.preview_custom_visual(source='window.mount=()=>{}',parameters={},manifest=CanvasSemanticManifestV1.model_validate(_manifest()))
    findings=result['views'][0]['findings']
    assert len(findings)==1 and 'vertexA' in findings[0]
    assert 'exact emitted semantic ID' in findings[0]



def test_preview_is_verified_before_refinement_and_final_plan(monkeypatch):
    import asyncio, json
    from types import SimpleNamespace
    from agents import RunContextWrapper
    o, context = _review_candidate(monkeypatch)
    context.custom_preview_valid = False
    context.current_preview_findings = ['Known technical defect']
    class Agent:
        name = 'composer'
        def clone(self, **kwargs): return SimpleNamespace(**{'name':self.name, 'tools':['bounded'], **kwargs})
    class Payload:
        def model_dump(self, **kwargs): return {}
    calls=[]
    async def run(agent, **kwargs):
        calls.append(agent.name)
        context.model_turns.append({})
        payload=json.loads(kwargs['input'][0]['content'][0]['text'])
        if agent.name == 'Lina Canvas verification':
            if len(calls)==1:
                assert payload['technical_findings']==['Known technical defect']
            return SimpleNamespace(final_output=_review(o,context.current_custom_candidate_block_id,accepted=len(calls)>1))
        if agent.tools:
            assert agent.tool_use_behavior is o._pause_after_candidate_preview
            o._refine_custom_visual(RunContextWrapper(context),edits=[o.CustomVisualSourceEditV1(before='"portion"',after='"corrected portion"')])
            assert o._pause_after_candidate_preview(RunContextWrapper(context),[]).is_final_output
            return SimpleNamespace(final_output='candidate-preview-ready')
        assert kwargs['max_turns']==1 and 'passed technical and independent' in payload['instruction']
        return SimpleNamespace(final_output=SimpleNamespace(visual_review=_review(o,context.current_custom_candidate_block_id)))
    monkeypatch.setattr(o.Runner,'run',run)
    _,attempts=asyncio.run(o._verify_and_correct_candidate(agent=Agent(),context=context,
        result=SimpleNamespace(final_output='candidate-preview-ready'),brief=Payload(),learner_context=Payload(),trace_id='trace-proof'))
    assert calls==['Lina Canvas verification','composer','Lina Canvas verification','composer']
    assert context.custom_preview_valid and context.reviewed_preview_count==context.custom_preview_count==2
    assert len(attempts)==5 and context.custom_attempt_count==2
    assert not o._pause_after_candidate_preview(RunContextWrapper(context),[]).is_final_output
