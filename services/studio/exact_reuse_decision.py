"""Jev routing over fully authorized, executable exact-reuse actions only."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.platform.db.models import (
    ModelTask,
    VisualArtifact,
    VisualArtifactBuild,
    VisualArtifactInstance,
    VisualArtifactVersion,
)
from services.platform.storage import ObjectStorage
from services.studio.agent.tools import create_reused_custom_visual
from services.studio.agentic_canvas import AGENTIC_CANVAS_SCENE_ADAPTER
from services.studio.canvas_brief import CanvasBriefV1
from services.studio.custom_visual_builds import CustomVisualBuildResolver
from services.studio.full_power_canvas import validate_visual_parameters


NO_MATCH = "NO_MATCH"
MAX_EXACT_REUSE_ACTIONS = 5


@dataclass(frozen=True)
class ExactReuseAction:
    action_id: str
    instance_id: UUID
    version_id: UUID
    semantic_purpose: str
    stable_slug: str
    parameters: dict[str, object]
    manifest_summary: dict[str, object]


@dataclass(frozen=True)
class ExactReuseDecision:
    status: str
    policy_version: str
    selected_action_id: str | None
    selected_probability: float | None
    margin: float | None
    probabilities: dict[str, float]
    ai_execution_id: UUID | None
    failure_code: str | None = None

    def audit_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "policy_version": self.policy_version,
            "selected_action_id": self.selected_action_id,
            "selected_probability": self.selected_probability,
            "margin": self.margin,
            "probabilities": self.probabilities,
            "ai_execution_id": None if self.ai_execution_id is None else str(self.ai_execution_id),
            "failure_code": self.failure_code,
        }


def load_exact_reuse_actions(
    session: Session, *, student_id: UUID
) -> list[ExactReuseAction]:
    """Load recent same-learner frozen instances that remain executable."""

    rows = session.execute(
        select(VisualArtifactInstance, VisualArtifactVersion, VisualArtifact, VisualArtifactBuild)
        .join(VisualArtifactVersion, VisualArtifactVersion.id == VisualArtifactInstance.artifact_version_id)
        .join(VisualArtifact, VisualArtifact.id == VisualArtifactVersion.artifact_id)
        .join(VisualArtifactBuild, VisualArtifactBuild.id == VisualArtifactVersion.implementation_build_id)
        .where(
            VisualArtifactInstance.student_id == student_id,
            VisualArtifact.runtime_kind == "custom-visual",
            VisualArtifact.lifecycle_status.in_(("VALIDATED", "TRUSTED")),
            VisualArtifactVersion.validation_status.in_(("VALIDATED", "TRUSTED")),
            VisualArtifactBuild.status == "VALIDATED",
        )
        .order_by(VisualArtifactInstance.created_at.desc())
        .limit(MAX_EXACT_REUSE_ACTIONS)
    ).all()
    actions: list[ExactReuseAction] = []
    for index, (instance, version, artifact, build) in enumerate(rows):
        try:
            parameters = dict(instance.bound_parameters)
            validate_visual_parameters(dict(version.parameter_schema), parameters)
        except (TypeError, ValueError):
            continue
        if (
            version.implementation_build_id != build.id
            or version.source_digest != build.source_digest
            or not isinstance(build.manifest_digest, str)
            or build.manifest_digest != (version.technical_evidence or {}).get("manifest_digest")
        ):
            continue
        actions.append(
            ExactReuseAction(
                action_id=f"REUSE_{index}",
                instance_id=instance.id,
                version_id=version.id,
                semantic_purpose=artifact.semantic_purpose,
                stable_slug=artifact.stable_slug,
                parameters=parameters,
                manifest_summary=_manifest_summary(dict(version.manifest_contract)),
            )
        )
    return actions


def decide_exact_reuse_action(
    gateway: ModelGateway,
    *,
    brief: CanvasBriefV1,
    actions: list[ExactReuseAction],
    min_probability: float,
    min_margin: float,
    policy_version: str,
    run_id: UUID,
    student_id: UUID,
    learning_session_id: UUID,
    source_message_id: UUID,
) -> ExactReuseDecision:
    if not actions:
        return ExactReuseDecision(
            status="NOT_APPLICABLE",
            policy_version=policy_version,
            selected_action_id=None,
            selected_probability=None,
            margin=None,
            probabilities={},
            ai_execution_id=None,
        )
    criteria = {
        action.action_id: (
            f"Exact replay of semantic purpose: {action.semantic_purpose}; "
            f"frozen instance parameters: {action.parameters}; capabilities: {action.manifest_summary}"
        )
        for action in actions
    }
    criteria[NO_MATCH] = (
        "No authorized action exactly satisfies the brief; new composition, new parameter binding, "
        "adaptation, or creation is needed."
    )
    try:
        result = gateway.execute(
            ModelTask.CANVAS_REUSE_SELECTION,
            {
                "state": {
                    "description": (
                        "Choose only among executable exact-replay actions. An action is not a template: "
                        "its parameters and capabilities are frozen. Prefer NO_MATCH for any mismatch."
                    ),
                    "canvas_brief": brief.model_dump(mode="json"),
                },
                "questions": {
                    "reuse_action": {
                        "type": "choice",
                        "instructions": (
                            "Select one exact replay only if it fully serves the educational brief as-is. "
                            "Do not assume new parameters, content, interactions, or capabilities."
                        ),
                        "criteria": criteria,
                    }
                },
            },
            lineage=AIExecutionLineage(
                operation="canvas_exact_reuse_selection",
                operation_id=run_id,
                student_id=student_id,
                learning_session_id=learning_session_id,
                source_message_id=source_message_id,
            ),
        )
        answer = result.output.get("answers")
        answer = answer.get("reuse_action") if isinstance(answer, dict) else None
        choice, probabilities = _choice_answer(answer)
        allowed = {action.action_id for action in actions} | {NO_MATCH}
        if choice not in allowed or set(probabilities) != allowed:
            raise ValueError("choice contract invalid")
        selected_probability = probabilities[choice]
        other = max((value for key, value in probabilities.items() if key != choice), default=0.0)
        margin = selected_probability - other
        accepted = (
            choice != NO_MATCH
            and selected_probability >= min_probability
            and margin >= min_margin
        )
        return ExactReuseDecision(
            status="ACCEPTED" if accepted else "FALLBACK",
            policy_version=policy_version,
            selected_action_id=choice if accepted else None,
            selected_probability=selected_probability,
            margin=margin,
            probabilities=probabilities,
            ai_execution_id=result.execution_id,
        )
    except Exception as error:
        return ExactReuseDecision(
            status="FAILED",
            policy_version=policy_version,
            selected_action_id=None,
            selected_probability=None,
            margin=None,
            probabilities={},
            ai_execution_id=None,
            failure_code=type(error).__name__,
        )


def materialize_exact_reuse_scene(
    session: Session,
    *,
    action: ExactReuseAction,
    brief: CanvasBriefV1,
    run_id: UUID,
    student_id: UUID,
    runtime_id: UUID,
    storage: ObjectStorage | None,
):
    """Freshly revalidate one selected action and build a reference-only Scene."""

    instance = session.execute(
        select(VisualArtifactInstance).where(
            VisualArtifactInstance.id == action.instance_id,
            VisualArtifactInstance.student_id == student_id,
            VisualArtifactInstance.artifact_version_id == action.version_id,
        )
    ).scalar_one_or_none()
    version = session.get(VisualArtifactVersion, action.version_id)
    artifact = session.get(VisualArtifact, version.artifact_id) if version is not None else None
    build = session.get(VisualArtifactBuild, version.implementation_build_id) if version is not None else None
    if (
        instance is None
        or version is None
        or artifact is None
        or build is None
        or artifact.lifecycle_status not in {"VALIDATED", "TRUSTED"}
        or version.validation_status not in {"VALIDATED", "TRUSTED"}
        or build.status != "VALIDATED"
        or version.source_digest != build.source_digest
        or build.manifest_digest != (version.technical_evidence or {}).get("manifest_digest")
        or dict(instance.bound_parameters) != action.parameters
    ):
        raise ValueError("Exact reuse action is stale or unauthorized.")
    parameters = dict(instance.bound_parameters)
    validate_visual_parameters(dict(version.parameter_schema), parameters)
    if storage is None:
        raise ValueError("Exact reuse requires configured visual storage.")
    CustomVisualBuildResolver(storage).resolve_artifact_version(
        session,
        version_id=version.id,
        student_id=student_id,
        runtime_id=runtime_id,
    )
    block_id = "reused-visual"
    block = create_reused_custom_visual(
        block_id=block_id,
        meaning=brief.objective,
        label=artifact.semantic_purpose[:120],
        artifact_instance_id=f"reuse-{run_id.hex[:24]}",
        bridge_nonce=sha256(f"{run_id}:exact-reuse".encode()).hexdigest()[:32],
        build_id=str(build.id),
        manifest_digest=str(build.manifest_digest),
        manifest=dict(version.manifest_contract),
        parameters=parameters,
    )
    return AGENTIC_CANVAS_SCENE_ADAPTER.validate_python(
        {
            "version": "agentic-canvas-scene-v3",
            "objective": brief.objective,
            "subject_key": brief.subject_key,
            "presentation": {
                "layout": "FOCUS",
                "palette": "AUTO",
                "motion": "SUBTLE",
                "placements": [
                    {"block_id": block_id, "role": "PRIMARY", "order": 0, "span": "FULL"}
                ],
                "reveal_order": [block_id],
            },
            "blocks": [block.model_dump(mode="json")],
        }
    )


def _manifest_summary(manifest: dict[str, object]) -> dict[str, object]:
    interactions = manifest.get("interactions")
    return {
        "representation": str(manifest.get("representation_summary", ""))[:600],
        "visual_descriptions": [str(item)[:160] for item in manifest.get("visual_descriptions", [])[:5]]
        if isinstance(manifest.get("visual_descriptions"), list)
        else [],
        "interactions": [
            {key: item.get(key) for key in ("semantic_id", "action", "meaning")}
            for item in interactions[:12]
            if isinstance(item, dict)
        ]
        if isinstance(interactions, list)
        else [],
    }


def _choice_answer(answer: object) -> tuple[str, dict[str, float]]:
    if not isinstance(answer, dict) or not isinstance(answer.get("choice"), str):
        raise ValueError("missing choice")
    raw = answer.get("probabilities")
    if not isinstance(raw, dict):
        raise ValueError("missing probabilities")
    probabilities: dict[str, float] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("invalid probability")
        probability = float(value)
        if not 0 <= probability <= 1:
            raise ValueError("invalid probability")
        probabilities[key] = probability
    return answer["choice"], probabilities
