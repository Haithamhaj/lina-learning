"""Non-authoritative Jev rubric comparison for validated Segment findings."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import get_args
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.intelligence.consolidation import (
    ConfidenceCalibration,
    EvidenceDimensions,
    EvidenceRelationship,
    Independence,
    Persistence,
    Reasoning,
    Retention,
    SelfCorrection,
    StrategyEffectiveness,
    Transfer,
    Understanding,
)
from services.intelligence.segment_reviews import (
    HistoricalEvidenceAnchor,
    SegmentLearningReviewEnvelope,
)
from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.platform.db.models import (
    LearningMessage,
    ModelTask,
    SegmentLearningReview,
    SegmentRubricDecisionShadow,
)


_DIMENSIONS = {
    "understanding": get_args(Understanding),
    "independence": get_args(Independence),
    "reasoning_demonstration": get_args(Reasoning),
    "transfer": get_args(Transfer),
    "self_correction": get_args(SelfCorrection),
    "retention": get_args(Retention),
    "strategy_effectiveness": get_args(StrategyEffectiveness),
    "persistence": get_args(Persistence),
    "confidence_calibration": get_args(ConfidenceCalibration),
}


def run_segment_rubric_shadow(
    session: Session,
    *,
    review: SegmentLearningReview,
    envelope: SegmentLearningReviewEnvelope,
    messages: list[LearningMessage],
    historical_anchors: list[HistoricalEvidenceAnchor],
    gateway: ModelGateway,
    policy_version: str,
) -> SegmentRubricDecisionShadow:
    """Persist a safe comparison that can never change Evidence authority."""

    route = gateway.route_for(ModelTask.SEGMENT_RUBRIC_DECISION)
    existing = session.execute(
        select(SegmentRubricDecisionShadow).where(
            SegmentRubricDecisionShadow.segment_review_id == review.id,
            SegmentRubricDecisionShadow.policy_version == policy_version,
            SegmentRubricDecisionShadow.provider == route.provider,
            SegmentRubricDecisionShadow.model == route.model,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    now = datetime.now(UTC)
    if not envelope.findings:
        shadow = SegmentRubricDecisionShadow(
            segment_review_id=review.id,
            policy_version=policy_version,
            rubric_version=review.rubric_version,
            provider=route.provider,
            model=route.model,
            status="NOT_APPLICABLE",
            output={"version": policy_version, "findings": []},
            completed_at=now,
        )
        session.add(shadow)
        session.flush()
        return shadow

    messages_by_id = {message.id: message for message in messages}
    anchors_by_id = {anchor.evidence_id: anchor for anchor in historical_anchors}
    records: list[dict[str, object]] = []
    for index, finding in enumerate(envelope.findings):
        cited = [messages_by_id.get(identifier) for identifier in finding.source_message_ids]
        method_source = messages_by_id.get(finding.teaching_method_source_tutor_message_id)
        anchor_records = [anchors_by_id.get(identifier) for identifier in finding.historical_anchor_evidence_ids]
        records.append(
            {
                "finding_index": index,
                "validated_event_type": finding.validated_event_type,
                "concept_ref": finding.concept_ref,
                "event_summary": finding.event_summary,
                "source_messages": [
                    {"id": str(message.id), "role": message.role, "content": message.content}
                    for message in cited
                    if message is not None
                ],
                "transfer_context": finding.transfer_context,
                "retention_context": finding.retention_context,
                "authority_facts": {
                    "method_lineage_available": method_source is not None and method_source.role == "tutor",
                    "teaching_method_id": None if finding.teaching_method_id is None else finding.teaching_method_id.value,
                    "teaching_method_source_tutor_message_id": (
                        None if method_source is None else str(method_source.id)
                    ),
                    "historical_anchor_availability": [
                        {
                            "evidence_id": str(anchor.evidence_id),
                            "concept_ref": anchor.concept_ref,
                            "broad_subject": anchor.broad_subject,
                            "elapsed_time": anchor.elapsed_time,
                        }
                        for anchor in anchor_records
                        if anchor is not None
                    ],
                },
            }
        )
    questions: dict[str, object] = {}
    for index, _finding in enumerate(envelope.findings):
        for dimension, options in _DIMENSIONS.items():
            questions[f"f{index}__{dimension}"] = {
                "type": "choice",
                "instructions": (
                    f"For finding_index {index}, select the supported {dimension} rubric state. "
                    "Use only cited messages and explicit authority_facts."
                ),
                "criteria": {option: _criterion(dimension, option) for option in options},
            }
        questions[f"f{index}__relationship"] = {
            "type": "choice",
            "instructions": (
                f"For finding_index {index}, select the evidence relationship supported by the observation."
            ),
            "criteria": {
                option: _criterion("relationship", option)
                for option in get_args(EvidenceRelationship)
            },
        }

    try:
        result = gateway.execute(
            ModelTask.SEGMENT_RUBRIC_DECISION,
            {
                "state": {
                    "description": (
                        "Already validated learning findings. Classify only bounded rubric fields. "
                        "Authority facts are explicit; absent authority must never be inferred."
                    ),
                    "primary_broad_subject": envelope.primary_broad_subject,
                    "findings": records,
                },
                "questions": questions,
            },
            lineage=AIExecutionLineage(
                operation="segment_rubric_shadow",
                operation_id=uuid5(NAMESPACE_URL, f"segment-rubric-shadow:{review.id}:{policy_version}"),
                student_id=review.student_id,
                learning_session_id=review.session_id,
                parent_execution_id=review.ai_execution_id,
            ),
        )
        answers = result.output.get("answers")
        if not isinstance(answers, dict):
            raise ValueError("missing answers")
        decisions: list[dict[str, object]] = []
        abstained = False
        for index, finding in enumerate(envelope.findings):
            selected: dict[str, str] = {}
            probabilities: dict[str, dict[str, float]] = {}
            for dimension, options in _DIMENSIONS.items():
                choice, values = _choice(answers.get(f"f{index}__{dimension}"), set(options))
                selected[dimension] = choice
                probabilities[dimension] = values
            relationship, relationship_probabilities = _choice(
                answers.get(f"f{index}__relationship"), set(get_args(EvidenceRelationship))
            )
            _apply_authority_overrides(
                selected,
                finding=finding,
                method_available=bool(records[index]["authority_facts"]["method_lineage_available"]),
                anchors_available=bool(records[index]["authority_facts"]["historical_anchor_availability"]),
            )
            try:
                dimensions = EvidenceDimensions.model_validate(selected)
                _validate_cross_fields(finding.validated_event_type, dimensions, relationship)
                status = "VALID"
            except Exception:
                abstained = True
                status = "ABSTAINED"
                dimensions = None
            luna_dimensions = finding.dimensions.model_dump(mode="json")
            jev_dimensions = None if dimensions is None else dimensions.model_dump(mode="json")
            decisions.append(
                {
                    "finding_index": index,
                    "status": status,
                    "dimensions": jev_dimensions,
                    "relationship": relationship if dimensions is not None else None,
                    "probabilities": {**probabilities, "relationship": relationship_probabilities},
                    "agreement_with_luna": (
                        jev_dimensions == luna_dimensions and relationship == finding.relationship
                        if dimensions is not None
                        else False
                    ),
                }
            )
        shadow = SegmentRubricDecisionShadow(
            segment_review_id=review.id,
            policy_version=policy_version,
            rubric_version=review.rubric_version,
            provider=route.provider,
            model=route.model,
            status="ABSTAINED" if abstained else "COMPLETED",
            output={"version": policy_version, "findings": decisions},
            ai_execution_id=result.execution_id,
            completed_at=datetime.now(UTC),
        )
    except Exception as error:
        shadow = SegmentRubricDecisionShadow(
            segment_review_id=review.id,
            policy_version=policy_version,
            rubric_version=review.rubric_version,
            provider=route.provider,
            model=route.model,
            status="FAILED",
            output=None,
            failure_code=type(error).__name__,
            completed_at=datetime.now(UTC),
        )
    session.add(shadow)
    session.flush()
    return shadow


def _choice(answer: object, allowed: set[str]) -> tuple[str, dict[str, float]]:
    if not isinstance(answer, dict) or not isinstance(answer.get("choice"), str):
        raise ValueError("invalid choice")
    raw = answer.get("probabilities")
    if answer["choice"] not in allowed or not isinstance(raw, dict) or set(raw) != allowed:
        raise ValueError("invalid choice")
    values = {
        key: float(value)
        for key, value in raw.items()
        if not isinstance(value, bool) and isinstance(value, (int, float)) and 0 <= value <= 1
    }
    if set(values) != allowed:
        raise ValueError("invalid probabilities")
    return answer["choice"], values


def _apply_authority_overrides(selected: dict[str, str], *, finding, method_available: bool, anchors_available: bool) -> None:
    if finding.validated_event_type != "transfer_attempt" or finding.transfer_context != "meaningfully_changed":
        selected["transfer"] = "not_tested"
    if finding.validated_event_type != "self_correction":
        selected["self_correction"] = "not_observed"
    if finding.validated_event_type != "retention_check" or not anchors_available:
        selected["retention"] = "not_tested"
    if finding.validated_event_type != "strategy_outcome" or not method_available:
        selected["strategy_effectiveness"] = "not_evaluable"


def _validate_cross_fields(event_type: str, dimensions: EvidenceDimensions, relationship: str) -> None:
    if dimensions.understanding == "strong_demonstration" and (
        dimensions.reasoning_demonstration != "well_supported"
        or dimensions.independence == "full_teaching"
    ):
        raise ValueError("unsupported strong demonstration")
    failed_retention = dimensions.retention in {"retrieval_failed", "partial_retrieval"}
    if failed_retention != (relationship == "retention_failure"):
        raise ValueError("retention relationship mismatch")
    if event_type != "retention_check" and dimensions.retention != "not_tested":
        raise ValueError("retention authority mismatch")


def _criterion(dimension: str, option: str) -> str:
    return f"Use {option} only when the cited observable behavior satisfies the project {dimension} rubric; otherwise prefer the explicit not-observed, not-tested, not-applicable, unclear, insufficient, or unrelated state available in this question."
