"""Unit contracts for distinct strategy Candidate Event meanings."""

from uuid import uuid4

import pytest

from services.intelligence.consolidation import ConsolidatedEvent
from services.tutor.candidate_events import (
    CandidateEventContractError,
    parse_candidate_event_metadata,
)


def _metadata(*, event_type: str, observed_student_outcome: str | None) -> tuple[dict[str, object], set]:
    source_message_id = uuid4()
    return (
        {
            "version": "candidate-event-v1",
            "candidates": [
                {
                    "event_type": event_type,
                    "concept_ref": "equivalent_fractions",
                    "summary": "The Tutor used a fraction bar representation.",
                    "signal": "fraction_bar_strategy",
                    "source_message_ids": [str(source_message_id)],
                    "school_or_extended": "school",
                    "observed_student_outcome": observed_student_outcome,
                }
            ],
        },
        {source_message_id},
    )


def test_strategy_applied_is_valid_without_an_observed_student_outcome() -> None:
    payload, source_ids = _metadata(event_type="strategy_applied", observed_student_outcome=None)

    metadata = parse_candidate_event_metadata(payload, allowed_source_message_ids=source_ids)

    assert metadata.candidates[0].event_type == "strategy_applied"
    assert metadata.candidates[0].observed_student_outcome is None


def test_strategy_outcome_still_requires_an_observed_student_outcome() -> None:
    payload, source_ids = _metadata(event_type="strategy_outcome", observed_student_outcome=None)

    with pytest.raises(CandidateEventContractError, match="violates"):
        parse_candidate_event_metadata(payload, allowed_source_message_ids=source_ids)


def test_new_tutor_candidate_metadata_rejects_deprecated_current_focus_signal() -> None:
    """Fail if a new Tutor turn can recreate school-position authority."""

    payload, source_ids = _metadata(
        event_type="current_focus_signal",
        observed_student_outcome=None,
    )

    with pytest.raises(CandidateEventContractError, match="violates"):
        parse_candidate_event_metadata(payload, allowed_source_message_ids=source_ids)


def test_foreign_misconception_candidate_source_is_filtered_without_rejecting_the_envelope() -> None:
    """CAND-01: an unavailable source can invalidate only its proposed misconception."""

    payload, source_ids = _metadata(event_type="misconception_signal", observed_student_outcome=None)
    payload["candidates"][0]["source_message_ids"] = [str(uuid4())]

    metadata = parse_candidate_event_metadata(payload, allowed_source_message_ids=source_ids)

    assert metadata.candidates == []


def test_historical_current_focus_signal_remains_readable_by_evidence_consolidation() -> None:
    """Keep historical raw Candidate Event lineage auditable and reprocessable."""

    candidate_id = uuid4()
    source_message_id = uuid4()

    event = ConsolidatedEvent.model_validate(
        {
            "candidate_event_id": str(candidate_id),
            "source_message_ids": [str(source_message_id)],
            "subject": "MATH",
            "concept_ref": "equivalent_fractions",
            "event_type": "current_focus_signal",
            "event_summary": "Historical source identified equivalent fractions.",
            "school_or_extended": "school",
            "dimensions": {
                "understanding": "not_observed",
                "independence": "not_applicable",
                "reasoning_demonstration": "not_observed",
                "transfer": "not_tested",
                "self_correction": "not_observed",
                "retention": "not_tested",
                "strategy_effectiveness": "not_evaluable",
                "persistence": "not_observed",
                "confidence_calibration": "not_observed",
            },
            "relationship": "insufficient",
        }
    )

    assert event.event_type == "current_focus_signal"
