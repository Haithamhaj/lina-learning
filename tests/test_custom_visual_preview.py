"""The real browser preview is bounded and cannot silently become syntax-only acceptance."""
import subprocess
import pytest
from services.studio import custom_visual_preview as preview


def test_preview_timeout_is_a_blocking_technical_failure(monkeypatch):
    def fail(*args, **kwargs):
        assert kwargs['timeout'] == 25
        raise subprocess.TimeoutExpired('node',25)
    monkeypatch.setattr(preview.subprocess,'run',fail)
    with pytest.raises(ValueError,match='PREVIEW_UNAVAILABLE'):
        preview.preview_custom_visual(source='window.mount=()=>{}',parameters={})


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
    o._refine_custom_visual(context,source=args['source']+';window.rendered=true;')
    assert not o._custom_visual_tool_enabled(context,None)
    assert context.context.current_custom_candidate_block_id=='first-refined'


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
