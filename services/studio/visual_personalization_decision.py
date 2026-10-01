"""Bounded Jev selection over an already filtered visual-fact catalogue."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.platform.db.models import ModelTask
from services.studio.canvas_brief import (
    VISUAL_CONTEXT_SELECTION_VERSION,
    CanvasBriefV1,
)


VISUAL_PERSONALIZATION_MAX_CANDIDATES = 12
VISUAL_MEMORY_SUPPORT_MAX_CANDIDATES = 18


@dataclass(frozen=True)
class VisualPersonalizationDecision:
    status: str
    policy_version: str
    selected_keys: tuple[str, ...]
    probabilities: dict[str, float]
    ai_execution_id: UUID | None
    failure_code: str | None = None

    def selection_payload(self) -> dict[str, object]:
        return {
            "version": VISUAL_CONTEXT_SELECTION_VERSION,
            "personal_fact_keys": list(self.selected_keys),
        }

    def audit_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "policy_version": self.policy_version,
            "selected_fact_keys": list(self.selected_keys),
            "probabilities": self.probabilities,
            "ai_execution_id": None if self.ai_execution_id is None else str(self.ai_execution_id),
            "failure_code": self.failure_code,
        }


@dataclass(frozen=True)
class VisualMemorySupportDecision:
    status: str
    policy_version: str
    selected_keys: tuple[str, ...]
    probabilities: dict[str, float]
    ai_execution_id: UUID | None
    failure_code: str | None = None

    def audit_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "policy_version": self.policy_version,
            "selected_support_keys": list(self.selected_keys),
            "probabilities": self.probabilities,
            "ai_execution_id": None if self.ai_execution_id is None else str(self.ai_execution_id),
            "failure_code": self.failure_code,
        }


def select_visual_memory_support(
    gateway: ModelGateway,
    *,
    brief: CanvasBriefV1,
    candidates: list[dict[str, object]],
    min_probability: float,
    policy_version: str,
    student_id: UUID,
    learning_session_id: UUID,
    source_message_id: UUID,
) -> VisualMemorySupportDecision:
    """Select up to three optional memory items; every other authority stays unchanged."""

    bounded = candidates[:VISUAL_MEMORY_SUPPORT_MAX_CANDIDATES]
    if not bounded:
        return VisualMemorySupportDecision(
            status="NOT_APPLICABLE",
            policy_version=policy_version,
            selected_keys=(),
            probabilities={},
            ai_execution_id=None,
        )

    questions = {
        f"support_{index}": {
            "type": "noul",
            "instructions": (
                f"For candidates[{index}] with support_key {str(candidate.get('support_key'))!r}, "
                "would this already-authorized optional memory support materially help the visual "
                "teacher serve the fixed educational target? Select only relevance; keep the target, "
                "academic truth, learner request, teaching authority, representation choice, and safety unchanged."
            ),
            "true_when": (
                "The memory item is directly useful optional support for understanding or tailoring "
                "this exact visual learning task."
            ),
            "false_when": (
                "The memory item is irrelevant, merely decorative, stale for this task, or would "
                "change the educational target or authority."
            ),
        }
        for index, candidate in enumerate(bounded)
    }
    selection_target = {
        "objective": brief.objective,
        "facts": list(brief.facts),
        "relations": [item.model_dump(mode="json") for item in brief.relations],
        "quantities": [item.model_dump(mode="json") for item in brief.quantities],
        "desired_student_action": brief.desired_student_action,
    }
    try:
        result = gateway.execute(
            ModelTask.CANVAS_VISUAL_PERSONALIZATION,
            {
                "state": {
                    "description": (
                        "Select optional memory support only. The educational target and all other "
                        "authorities are fixed reference input."
                    ),
                    "selection_target": selection_target,
                    "candidates": bounded,
                },
                "questions": questions,
            },
            lineage=AIExecutionLineage(
                operation="canvas_visual_memory_support",
                student_id=student_id,
                learning_session_id=learning_session_id,
                source_message_id=source_message_id,
            ),
        )
        answers = result.output.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("missing answers")
        scored: list[tuple[float, int, str]] = []
        probabilities: dict[str, float] = {}
        for index, candidate in enumerate(bounded):
            key = candidate.get("support_key")
            answer = answers.get(f"support_{index}")
            probability = _noul_probability(answer)
            if not isinstance(key, str) or probability is None:
                raise ValueError("invalid Noul answer")
            probabilities[key] = probability
            if probability >= min_probability:
                scored.append((probability, index, key))
        selected = tuple(
            key for _probability, _index, key
            in sorted(scored, key=lambda item: (-item[0], item[1]))[:3]
        )
        return VisualMemorySupportDecision(
            status="COMPLETED",
            policy_version=policy_version,
            selected_keys=selected,
            probabilities=probabilities,
            ai_execution_id=result.execution_id,
        )
    except Exception as error:
        return VisualMemorySupportDecision(
            status="FAILED",
            policy_version=policy_version,
            selected_keys=(),
            probabilities={},
            ai_execution_id=None,
            failure_code=type(error).__name__,
        )


def select_visual_personalization_facts(
    gateway: ModelGateway,
    *,
    brief: CanvasBriefV1,
    candidates: list[dict[str, str]],
    min_probability: float,
    policy_version: str,
    student_id: UUID,
    learning_session_id: UUID,
    source_message_id: UUID,
) -> VisualPersonalizationDecision:
    """Return up to three exact fact keys; failure safely selects no facts."""

    bounded = candidates[:VISUAL_PERSONALIZATION_MAX_CANDIDATES]
    if not bounded:
        return VisualPersonalizationDecision(
            status="NOT_APPLICABLE",
            policy_version=policy_version,
            selected_keys=(),
            probabilities={},
            ai_execution_id=None,
        )
    questions = {
        f"fact_{index}": {
            "type": "noul",
            "instructions": (
                f"For candidates[{index}] with fact_key {str(_candidate.get('fact_key'))!r}, would this "
                "already-authorized personal fact naturally improve the visual presentation "
                "of the Canvas brief without changing educational meaning, difficulty, teaching method, "
                "safety, or authority? Answer no when relevance is weak or merely decorative."
            ),
            "true_when": (
                "The fact is directly useful as optional presentation flavor for this exact brief."
            ),
            "false_when": (
                "The fact is unrelated, weakly related, merely decorative, or would alter educational meaning."
            ),
        }
        for index, _candidate in enumerate(bounded)
    }
    try:
        result = gateway.execute(
            ModelTask.CANVAS_VISUAL_PERSONALIZATION,
            {
                "state": {
                    "description": (
                        "A validated educational Canvas brief and a finite server-filtered catalogue. "
                        "Facts are optional presentation input only."
                    ),
                    "canvas_brief": brief.model_dump(mode="json"),
                    "candidates": bounded,
                },
                "questions": questions,
            },
            lineage=AIExecutionLineage(
                operation="canvas_visual_personalization",
                student_id=student_id,
                learning_session_id=learning_session_id,
                source_message_id=source_message_id,
            ),
        )
        answers = result.output.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("missing answers")
        scored: list[tuple[float, int, str]] = []
        probabilities: dict[str, float] = {}
        for index, candidate in enumerate(bounded):
            key = candidate.get("fact_key")
            answer = answers.get(f"fact_{index}")
            probability = _noul_probability(answer)
            if not isinstance(key, str) or probability is None:
                raise ValueError("invalid Noul answer")
            probabilities[key] = probability
            if probability >= min_probability:
                scored.append((probability, index, key))
        selected = tuple(key for _probability, _index, key in sorted(scored, key=lambda item: (-item[0], item[1]))[:3])
        return VisualPersonalizationDecision(
            status="COMPLETED",
            policy_version=policy_version,
            selected_keys=selected,
            probabilities=probabilities,
            ai_execution_id=result.execution_id,
        )
    except Exception as error:
        return VisualPersonalizationDecision(
            status="FAILED",
            policy_version=policy_version,
            selected_keys=(),
            probabilities={},
            ai_execution_id=None,
            failure_code=type(error).__name__,
        )


def _noul_probability(answer: object) -> float | None:
    if not isinstance(answer, dict):
        return None
    value = answer.get("noul")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    probability = float(value)
    return probability if 0 <= probability <= 1 else None
