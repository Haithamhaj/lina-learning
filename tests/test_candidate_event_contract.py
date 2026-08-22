"""Unit contracts for distinct strategy Candidate Event meanings."""

from uuid import uuid4

import pytest

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
