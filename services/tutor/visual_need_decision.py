"""Bounded pre-Tutor decision for whether existing Canvas would materially help."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.platform.db.models import ModelTask


_VISUAL_NEEDS = ("NONE", "HELPFUL", "STRONGLY_RECOMMENDED")
_VISUAL_CATEGORIES = ("NONE", "SHAPE", "STRUCTURE", "PROCESS", "SCENE")
_EXPLICIT_VISUAL = re.compile(
    r"(?:\b(?:draw|diagram|picture|visual|show\s+me\s+(?:a\s+)?(?:diagram|picture|visual))\b|"
    r"(?:ارسم|ارسمي|رسم|مخطط|صورة|وريني|ورّيني|وضحها بصري))",
    re.IGNORECASE,
)
_NO_VISUAL = re.compile(
    r"(?:\b(?:no\s+(?:picture|diagram|visual)|without\s+(?:a\s+)?(?:picture|diagram|visual)|"
    r"just\s+explain(?:\s+it)?(?:\s+in\s+words)?|text\s+only)\b|"
    r"(?:بدون\s+(?:صورة|رسم|مخطط)|اشرح(?:ها)?\s+(?:بالكلام|نص)|ما\s+بدي\s+(?:صورة|رسم|مخطط)))",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class VisualNeedDecision:
    status: str
    visual_need: str
    visual_category: str
    need_probability: float | None
    category_probability: float | None
    probabilities: dict[str, dict[str, float]]
    ai_execution_id: UUID | None
    failure_code: str | None = None
    source: str = "JEV"

    @property
    def recommends_visual(self) -> bool:
        return self.visual_need in {"HELPFUL", "STRONGLY_RECOMMENDED"}

    def tutor_signal(self) -> dict[str, object]:
        signal: dict[str, object] = {
            "status": self.status,
            "visual_category": self.visual_category,
            "source": self.source,
            "authority": "advisory_current_turn",
        }
        signal["visual_need"] = (
            self.visual_need
            if self.status == "COMPLETED" or self.source in {
                "STUDENT_NO_VISUAL", "EXPLICIT_VISUAL_REQUEST", "EQUIVALENT_VISUAL_IN_FLIGHT"
            }
            else "UNEVALUATED"
        )
        return signal

    def audit_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "visual_need": self.visual_need,
            "visual_category": self.visual_category,
            "need_probability": self.need_probability,
            "category_probability": self.category_probability,
            "probabilities": self.probabilities,
            "ai_execution_id": None if self.ai_execution_id is None else str(self.ai_execution_id),
            "failure_code": self.failure_code,
            "source": self.source,
        }


def decide_visual_need(
    gateway: ModelGateway | None,
    *,
    student_text: str,
    subject: str | None,
    current_exchange: list[dict[str, str]] | None = None,
    prior_teaching_method: str | None,
    current_canvas_status: str | None,
    capability_available: bool,
    source_meaning_clear: bool,
    min_probability: float,
    policy_version: str,
    student_id: UUID,
    learning_session_id: UUID,
    source_message_id: UUID,
) -> VisualNeedDecision:
    """Return one bounded signal; deterministic known states bypass the model."""

    normalized = student_text.strip()
    if _NO_VISUAL.search(normalized):
        return _deterministic("NONE", "NONE", "STUDENT_NO_VISUAL")
    if current_canvas_status in {"PENDING", "RUNNING"}:
        return _deterministic("NONE", "NONE", "EQUIVALENT_VISUAL_IN_FLIGHT")
    if _EXPLICIT_VISUAL.search(normalized):
        return _deterministic(
            "STRONGLY_RECOMMENDED", "NONE", "EXPLICIT_VISUAL_REQUEST"
        )
    if not capability_available or not source_meaning_clear:
        return _deterministic("NONE", "NONE", "NOT_ELIGIBLE")
    if gateway is None:
        return VisualNeedDecision(
            status="NOT_CONFIGURED",
            visual_need="NONE",
            visual_category="NONE",
            need_probability=None,
            category_probability=None,
            probabilities={},
            ai_execution_id=None,
            source="NONE",
        )

    questions = {
        "visual_need": {
            "type": "choice",
            "instructions": (
                "Decide whether the existing Lina Canvas would materially improve understanding "
                "for this exact current turn. Prefer NONE when concise conversation is sufficient; "
                "HELPFUL when a visual would add clear value; STRONGLY_RECOMMENDED when the concept "
                "is primarily visual/spatial/process-based or the current verbal representation is insufficient."
            ),
            "criteria": {
                "NONE": "Chat alone is sufficient for the current teaching need.",
                "HELPFUL": "A visual would materially improve clarity but is not essential.",
                "STRONGLY_RECOMMENDED": (
                    "A supported visual should normally be part of this teaching move."
                ),
            },
        },
        "visual_category": {
            "type": "choice",
            "instructions": (
                "Choose the single visual category that best describes the current educational need. "
                "Choose NONE when no meaningful visual need exists."
            ),
            "criteria": {
                "NONE": "No visual representation is materially useful.",
                "SHAPE": "Understanding depends on form, geometry, orientation, or spatial shape.",
                "STRUCTURE": "Understanding depends on parts, composition, layers, or arrangement.",
                "PROCESS": "Understanding depends on stages, sequence, flow, transformation, or cycle.",
                "SCENE": "Understanding depends on spatial relationships in a situation or scene.",
            },
        },
    }
    try:
        result = gateway.execute(
            ModelTask.VISUAL_NEED_DECISION,
            {
                "state": {
                    "description": (
                        "One current learner turn for a bounded visual-need classification. "
                        "This is not permission to author a Canvas or change teaching authority."
                    ),
                    "policy_version": policy_version,
                    "student_text": normalized,
                    "subject": subject,
                    "current_exchange": current_exchange or [],
                    "prior_teaching_method": prior_teaching_method,
                    "current_canvas_status": current_canvas_status,
                    "capability_available": capability_available,
                    "source_meaning_clear": source_meaning_clear,
                },
                "questions": questions,
            },
            lineage=AIExecutionLineage(
                operation="visual_need_decision",
                student_id=student_id,
                learning_session_id=learning_session_id,
                source_message_id=source_message_id,
            ),
        )
        answers = result.output.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("missing answers")
        need, need_probs = _choice(answers.get("visual_need"), set(_VISUAL_NEEDS))
        category, category_probs = _choice(
            answers.get("visual_category"), set(_VISUAL_CATEGORIES)
        )
        need_probability = need_probs[need]
        category_probability = category_probs[category]
        if need != "NONE" and need_probability < min_probability:
            need = "NONE"
            category = "NONE"
        if need == "NONE":
            category = "NONE"
        elif category == "NONE":
            raise ValueError("visual category missing for recommended visual")
        return VisualNeedDecision(
            status="COMPLETED",
            visual_need=need,
            visual_category=category,
            need_probability=need_probability,
            category_probability=category_probability,
            probabilities={
                "visual_need": need_probs,
                "visual_category": category_probs,
            },
            ai_execution_id=result.execution_id,
        )
    except Exception as error:
        return VisualNeedDecision(
            status="FAILED",
            visual_need="NONE",
            visual_category="NONE",
            need_probability=None,
            category_probability=None,
            probabilities={},
            ai_execution_id=None,
            failure_code=type(error).__name__,
        )


def _deterministic(need: str, category: str, source: str) -> VisualNeedDecision:
    return VisualNeedDecision(
        status="BYPASS",
        visual_need=need,
        visual_category=category,
        need_probability=1.0,
        category_probability=1.0 if category != "NONE" else None,
        probabilities={},
        ai_execution_id=None,
        source=source,
    )


def _choice(answer: object, allowed: set[str]) -> tuple[str, dict[str, float]]:
    if not isinstance(answer, dict) or not isinstance(answer.get("choice"), str):
        raise ValueError("invalid choice")
    selected = answer["choice"]
    raw = answer.get("probabilities")
    if selected not in allowed or not isinstance(raw, dict) or set(raw) != allowed:
        raise ValueError("invalid choice")
    probabilities: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("invalid probability")
        probability = float(value)
        if not 0 <= probability <= 1:
            raise ValueError("invalid probability")
        probabilities[key] = probability
    return selected, probabilities
