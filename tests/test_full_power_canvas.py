from __future__ import annotations

import pytest
from pydantic import ValidationError


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

    with pytest.raises(ValidationError, match="forbidden API"):
        CustomVisualPackageV1.model_validate({
            "version": "custom-visual-package-v1",
            "runtime_kind": "custom-visual",
            "dependencies": ["native-svg-v1"],
            "source": "window.mount = () => fetch('https://example.test')",
            "manifest": _manifest(),
            "parameter_schema": {"type": "object", "properties": {}},
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
                "definition": {"dependencies": ["native-svg-v1"], "source": "window.mount=(root,params,bridge)=>{root.textContent=params.left}"},
            }
        },
    )

    class Wrapper:
        def __init__(self): self.context = context

    response = _instantiate_reusable_visual(
        Wrapper(), version_id="version-1", block_id="reused-ruler", meaning="Compare exact fractions.", label="Shared fraction ruler",
        artifact_instance_id="reused-instance", bridge_nonce="nonce-123", manifest_json=__import__("json").dumps(_manifest()), parameters_json='{"left":"1/2"}', mode="REUSE",
    )
    assert response["type"] == "CUSTOM_VISUAL"
    assert context.reusable_selections[0]["mode"] == "REUSE"
    assert "window.mount" not in str(response)
