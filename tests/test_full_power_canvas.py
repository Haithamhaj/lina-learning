from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_syntax_diagnostic_locates_failure_without_source_or_execution():
    from services.studio.full_power_canvas import _validate_javascript_syntax, CustomVisualSecurityError
    from services.studio.agent.orchestrator import _custom_visual_error_payload
    _validate_javascript_syntax("throw new Error('must not execute');")
    with pytest.raises(CustomVisualSecurityError) as caught:
        _validate_javascript_syntax("// private-marker-not-for-diagnostics\nwindow.mount = => {};")
    payload = _custom_visual_error_payload(caught.value)
    assert payload['syntax_diagnostic']['line'] == 2
    assert payload['syntax_diagnostic']['category'] == 'Unexpected token'
    assert 'private-marker' not in str(payload)
    assert 'window.mount' not in str(payload)


@pytest.mark.parametrize("source", [
    "window.mount=(root,params,bridge)=>{",
    "window.mount=(root,params,bridge)=>bridge.emit({action:'SELECT',semantic_id:'fraction-a',value:'3/4'})",
])
def test_custom_visual_rejects_broken_syntax_and_object_bridge_binding(source):
    from services.studio.full_power_canvas import CustomVisualPackageV1
    with pytest.raises(ValidationError, match="SYNTAX_INVALID|SEMANTIC_INTERACTION_BINDING_INVALID"):
        CustomVisualPackageV1.model_validate({
            "version": "custom-visual-package-v1", "runtime_kind": "custom-visual",
            "dependencies": ["native-svg-v1"], "source": source, "manifest": _manifest(),
        })


def _manifest() -> dict[str, object]:
    return {
        "version": "canvas-semantic-manifest-v1",
        "brief_digest": "a" * 64,
        "objective": "Compare two exact fractions.",
        "representation_summary": "A movable fraction comparison on one shared number line.",
        "entities": [
            {
                "semantic_id": "fraction-a",
                "kind": "quantity",
                "label": "one half",
                "educational_meaning": "The first exact fraction.",
                "visible_description": "The blue marker.",
            },
        ],
        "relations": [],
        "quantities": [{"semantic_id": "fraction-a", "value": "1/2", "unit": None, "provenance": "tutor-brief"}],
        "presentation_steps": [{"semantic_id": "compare", "label": "Compare", "order": 1}],
        "interactions": [{"semantic_id": "fraction-a", "action": "MOVE", "meaning": "Move the fraction marker.", "value_required": True}],
        "calculated_results": [],
        "visual_descriptions": ["A blue marker represents one half."],
        "current_state_schema": {"active_focus": "semantic-id"},
        "provenance": {"brief_digest": "a" * 64, "runtime_kind": "custom-visual"},
    }


def test_custom_visual_rejects_network_source_before_a_sandbox_exists() -> None:
    from services.studio.full_power_canvas import CustomVisualPackageV1, CustomVisualSecurityError

    with pytest.raises(ValidationError, match="CUSTOM_VISUAL_FORBIDDEN_API:fetch"):
        CustomVisualPackageV1.model_validate({
            "version": "custom-visual-package-v1",
            "runtime_kind": "custom-visual",
            "dependencies": ["native-svg-v1"],
            "source": "window.mount = () => fetch('https://example.test')",
            "manifest": _manifest(),
            "parameter_schema": {"type": "object", "properties": {}},
        })


def test_ordinary_function_expression_is_not_the_dynamic_function_constructor():
    from services.studio.full_power_canvas import CustomVisualPackageV1
    payload = {"version": "custom-visual-package-v1", "runtime_kind": "custom-visual",
        "dependencies": ["native-svg-v1"], "manifest": _manifest(),
        "source": "window.mount=function(root,params,bridge){root.textContent='Compare';};"}
    assert CustomVisualPackageV1.model_validate(payload).source == payload["source"]
    with pytest.raises(ValidationError, match="FORBIDDEN_API:function"):
        CustomVisualPackageV1.model_validate({**payload, "source": "window.mount=Function('return 1');"})


def test_custom_visual_rejects_html_controls_appended_to_svg_parent() -> None:
    """A declared choice must be visible and usable in the opaque sandbox."""
    from services.studio.full_power_canvas import CustomVisualPackageV1

    with pytest.raises(ValidationError, match="CONTROL_NOT_RENDERABLE"):
        CustomVisualPackageV1.model_validate({
            "version": "custom-visual-package-v1", "runtime_kind": "custom-visual",
            "dependencies": ["native-svg-v1"],
            "source": "window.mount=(root)=>{const svg=document.createElementNS('x','svg');root.appendChild(svg);const b=document.createElement('button');svg.parentNode.appendChild(b)}",
            "manifest": _manifest(), "parameter_schema": {"type": "object", "properties": {}},
        })


def test_custom_visual_allows_shared_handlers_with_runtime_manifest_enforcement() -> None:
    from services.studio.full_power_canvas import CustomVisualPackageV1
    package = CustomVisualPackageV1.model_validate({
        "version": "custom-visual-package-v1", "runtime_kind": "custom-visual",
        "dependencies": ["native-svg-v1"],
        "source": "window.mount=(root,params,bridge)=>{const id='fraction-a';bridge.emit('MOVE',id,{to_value:'3/4'})}",
        "manifest": _manifest(), "parameter_schema": {"type": "object", "properties": {}},
    })
    assert package.manifest.interactions[0].semantic_id == "fraction-a"


def test_custom_visual_rejects_bridge_tuple_not_declared_by_manifest() -> None:
    from services.studio.full_power_canvas import CustomVisualPackageV1

    with pytest.raises(ValidationError, match="SEMANTIC_INTERACTION_BINDING_INVALID"):
        CustomVisualPackageV1.model_validate({
            "version": "custom-visual-package-v1", "runtime_kind": "custom-visual",
            "dependencies": ["native-svg-v1"],
            "source": "window.mount=(root,params,bridge)=>bridge.emit('SELECT','fraction-a',{})",
            "manifest": _manifest(), "parameter_schema": {"type": "object", "properties": {}},
        })


def test_registry_keeps_private_instance_values_out_of_reusable_definition() -> None:
    from services.studio.full_power_canvas import ReusableVisualArtifactService, VisualArtifactPrivacyError

    registry = ReusableVisualArtifactService()
    with pytest.raises(VisualArtifactPrivacyError, match="student-private"):
        registry.create_candidate(
            stable_slug="fraction-comparison",
            semantic_purpose="Compare exact fractions",
            runtime_kind="typed-agentic-canvas",
            parameter_schema={"type": "object", "properties": {"left": {"type": "string"}}},
            manifest_contract=_manifest(),
            definition={"label": "Lina's private hobby"},
        )


def test_semantic_bridge_accepts_declared_action_and_rejects_undeclared_action() -> None:
    from services.studio.full_power_canvas import CanvasSemanticBridge, SemanticBridgeError

    bridge = CanvasSemanticBridge(manifest=_manifest(), artifact_instance_id="instance-1", nonce="nonce-123")
    accepted = bridge.validate({
        "version": "canvas-semantic-event-v1",
        "artifact_instance_id": "instance-1",
        "nonce": "nonce-123",
        "semantic_action": "MOVE",
        "semantic_id": "fraction-a",
        "from_value": "1/2",
        "to_value": "3/4",
        "idempotency_key": "move-1",
    })
    assert accepted.semantic_id == "fraction-a"
    with pytest.raises(SemanticBridgeError, match="not declared"):
        bridge.validate({
            "version": "canvas-semantic-event-v1",
            "artifact_instance_id": "instance-1",
            "nonce": "nonce-123",
            "semantic_action": "SUBMIT",
            "semantic_id": "fraction-a",
            "idempotency_key": "submit-1",
        })


def test_custom_package_materializes_only_as_a_v3_agentic_scene() -> None:
    from services.studio.agent.registry import CanvasBlockRegistry
    from services.studio.agent.tools import create_custom_visual
    from services.studio.agentic_canvas import AgenticCanvasPlanV1

    registry = CanvasBlockRegistry()
    registry.accept(create_custom_visual(
        block_id="fraction-custom",
        meaning="Move the exact blue fraction marker.",
        label="Fraction comparison",
        artifact_instance_id="fraction-instance",
        bridge_nonce="nonce-123",
        dependencies=["native-svg-v1"],
        source="window.mount=(root,params,bridge)=>{root.textContent=params.label}",
        manifest=_manifest(),
        parameter_schema={"type": "object", "properties": {"label": {"type": "string"}}},
        parameters={"label": "1/2"},
    ))
    scene = registry.materialize_plan(AgenticCanvasPlanV1.model_validate({
        "version": "agentic-canvas-plan-v1", "objective": "Compare fractions.", "subject_key": "MATH",
        "layout": "FOCUS", "palette": "COOL", "motion": "NONE",
        "placements": [{"block_id": "fraction-custom", "role": "PRIMARY", "order": 0, "span": "FULL"}], "reveal_order": [],
    }))
    assert scene.version == "agentic-canvas-scene-v3"


def test_create_candidate_requires_a_coherent_registered_final_plan() -> None:
    """CREATE may supersede candidates, but cannot silently fall back to typed blocks."""
    from services.studio.agent.registry import (
        CanvasBlockRegistry,
        PlanCompositionInconsistencyError,
    )
    from services.studio.agent.tools import create_custom_visual, create_math_input
    from services.studio.agentic_canvas import AgenticCanvasPlanV1

    registry = CanvasBlockRegistry()
    earlier = registry.accept(create_custom_visual(
        block_id="earlier-custom", meaning="An earlier coupled view.", label="Earlier",
        artifact_instance_id="earlier-instance", bridge_nonce="nonce-123", dependencies=["native-svg-v1"],
        source="window.mount=(root)=>{root.textContent='earlier'}", manifest=_manifest(),
        parameter_schema={"type": "object", "properties": {}},
    ))
    current = registry.accept(create_custom_visual(
        block_id="current-custom", meaning="The selected coupled view.", label="Current",
        artifact_instance_id="current-instance", bridge_nonce="nonce-456", dependencies=["native-svg-v1"],
        source="window.mount=(root)=>{root.textContent='current'}", manifest=_manifest(),
        parameter_schema={"type": "object", "properties": {}},
    ))
    registry.accept(create_math_input(
        block_id="typed-support", meaning="A supporting answer.", label="Answer",
        prompt="Choose the steeper line.", initial_value="", constraints=[],
    ))

    def plan(*block_ids: str) -> AgenticCanvasPlanV1:
        return AgenticCanvasPlanV1.model_validate({
            "version": "agentic-canvas-plan-v1", "objective": "Compare slopes.", "subject_key": "MATH",
            "layout": "FOCUS_SUPPORT", "palette": "COOL", "motion": "NONE",
            "placements": [
                {"block_id": block_id, "role": "PRIMARY" if index == 0 else "SUPPORT", "order": index, "span": "FULL" if index == 0 else "NORMAL"}
                for index, block_id in enumerate(block_ids)
            ],
            "reveal_order": [],
        })

    with pytest.raises(PlanCompositionInconsistencyError, match="PLAN_COMPOSITION_INCONSISTENT"):
        registry.materialize_plan(plan("typed-support"), current_custom_candidate_block_id=current.block_id)

    repaired = registry.materialize_plan(
        plan(current.block_id, "typed-support"),
        current_custom_candidate_block_id=current.block_id,
    )
    assert repaired.version == "agentic-canvas-scene-v3"
    assert [block.block_id for block in repaired.blocks] == [current.block_id, "typed-support"]

    with pytest.raises(ValueError, match="not produced by a registered tool"):
        registry.materialize_plan(
            plan(current.block_id, "unregistered-custom"),
            current_custom_candidate_block_id=current.block_id,
        )

    # The current candidate supersedes the earlier valid package; it is not required.
    assert earlier.block_id not in {block.block_id for block in repaired.blocks}


def test_tutor_projection_exposes_manifest_without_generated_source() -> None:
    from services.studio.agent.tools import create_custom_visual
    from services.studio.agentic_canvas import build_agentic_tutor_projection

    block = create_custom_visual(
        block_id="fraction-custom", meaning="Move the exact blue fraction marker.", label="Fraction comparison",
        artifact_instance_id="fraction-instance", bridge_nonce="nonce-123", dependencies=["native-svg-v1"],
        source="window.mount=(root,params,bridge)=>{root.textContent=params.label}", manifest=_manifest(),
        parameter_schema={"type": "object", "properties": {"label": {"type": "string"}}}, parameters={"label": "1/2"},
    )
    projection = build_agentic_tutor_projection(
        objective="Compare fractions.", subject_key="MATH", scene_status="ACTIVE", blocks=[block.model_dump(mode="json")], actions=[],
    )
    encoded = str(projection)
    assert projection["blocks"][0]["semantic_manifest"]["representation_summary"].startswith("A movable")
    assert "window.mount" not in encoded


def test_tutor_projection_for_reference_custom_visual_uses_resolved_manifest() -> None:
    """A settled Scene carries a build reference, never generated implementation."""
    from services.studio.agentic_canvas import build_agentic_tutor_projection

    block = {
        "block_id": "fraction-custom",
        "type": "CUSTOM_VISUAL",
        "meaning": "Move the exact blue fraction marker.",
        "title": "Fraction comparison",
        "accessibility": {"text_equivalent": "A movable fraction.", "aria_label": None},
        "allowed_actions": ["MOVE"],
        "elements": [{"id": "fraction-a", "label": "one half", "current_value": "1/2"}],
        "artifact_instance_id": "fraction-instance",
        "bridge_nonce": "nonce-123",
        "custom_visual_build_id": "555f790a-c452-49df-b009-b0178a403783",
        "manifest_digest": "b" * 64,
        "parameters": {"label": "1/2"},
    }
    projection = build_agentic_tutor_projection(
        objective="Compare fractions.",
        subject_key="MATH",
        scene_status="ACTIVE",
        blocks=[block],
        actions=[],
        resolved_custom_manifests={block["block_id"]: _manifest()},
    )

    assert projection["blocks"][0]["semantic_manifest"]["representation_summary"].startswith("A movable")
    assert "package" not in str(projection)


def test_reusable_custom_visual_is_instantiated_from_a_version_without_exposing_its_source() -> None:
    from services.studio.agent.orchestrator import CanvasAgentRunContext, _instantiate_reusable_visual
    from services.studio.agent.registry import CanvasBlockRegistry

    context = CanvasAgentRunContext(
        registry=CanvasBlockRegistry(),
        reusable_visuals={
            "version-1": {
                "stable_slug": "fraction-ruler",
                "semantic_purpose": "Compare exact fractions on a shared ruler.",
                "runtime_kind": "custom-visual",
                "parameter_schema": {"type": "object", "properties": {"left": {"type": "string"}}},
                "implementation_build_id": "555f790a-c452-49df-b009-b0178a403783",
                "manifest_digest": "b" * 64,
                "manifest_contract": _manifest(),
            }
        },
    )

    class Wrapper:
        def __init__(self): self.context = context

    response = _instantiate_reusable_visual(
        Wrapper(), version_id="version-1", block_id="reused-ruler", meaning="Compare exact fractions.", label="Shared fraction ruler",
        artifact_instance_id="reused-instance", bridge_nonce="nonce-123", parameters={"left": "1/2"}, mode="REUSE",
    )
    assert response["type"] == "CUSTOM_VISUAL"
    assert context.reusable_selections[0]["mode"] == "REUSE"
    assert "window.mount" not in str(response)
    assert "package" not in response
    block = next(block for block in context.registry.blocks() if block.block_id == "reused-ruler")
    assert block.package is None
    assert block.custom_visual_build_id == "555f790a-c452-49df-b009-b0178a403783"
    assert [item.model_dump(mode="json") for item in block.semantic_interactions] == [
        {"semantic_id": "fraction-a", "action": "MOVE", "value_required": True}
    ]
