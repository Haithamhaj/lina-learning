"""Pure contract tests for SUBJ-01 Subject attribution."""

import pytest
from types import SimpleNamespace
from uuid import UUID

from services.intelligence.segment_reviews import (
    LEGACY_SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
    SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
    SEGMENT_REVIEW_RESPONSE_SCHEMA,
    SegmentLearningReviewEnvelope,
    SegmentLearningReviewV3Envelope,
    SegmentReviewValidationError,
    validate_live_segment_review_output,
)


def test_v3_learning_review_has_one_primary_broad_subject_and_finding_concepts() -> None:
    """Catches the Review contract retaining Session-relative Subject authority."""

    review = SegmentLearningReviewV3Envelope.model_validate(
        {
            "version": SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
            "segment_kind": "LEARNING",
            "primary_broad_subject": "MATH",
            "school_context": {
                "school_relation": "UNKNOWN",
                "school_subject_ref": None,
                "school_domain_path": [],
                "unit_ref": None,
                "lesson_ref": None,
                "page_refs": [],
                "source_refs": [],
            },
            "findings": [],
        }
    )

    assert SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION == "segment-learning-review-v3"
    assert review.segment_kind == "LEARNING"
    assert review.primary_broad_subject == "MATH"
    assert review.school_context is not None
    assert review.school_context.school_relation == "UNKNOWN"


def test_v3_response_schema_exposes_review_level_subject_authority() -> None:
    """Catches the Model Gateway receiving the obsolete v1 Review schema."""

    schema = SEGMENT_REVIEW_RESPONSE_SCHEMA["schema"]

    assert SEGMENT_REVIEW_RESPONSE_SCHEMA["name"] == "segment_learning_review_v3"
    assert schema["properties"]["version"]["const"] == SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
    assert schema["properties"]["primary_broad_subject"]
    assert schema["properties"]["segment_kind"]
    assert set(schema["properties"]).issubset(set(schema["required"]))


def test_live_review_validation_rejects_historical_v2_output() -> None:
    """Historical v2 remains auditable, but cannot complete a v3 live Review."""

    with pytest.raises(SegmentReviewValidationError):
        validate_live_segment_review_output(
            {"version": LEGACY_SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION, "findings": []},
            messages=[],
            candidates=[],
        )


def _v3_finding(**overrides: object) -> dict[str, object]:
    finding: dict[str, object] = {
        "validated_event_type": "learning_attempt",
        "concept_ref": "equivalent_fractions",
        "event_summary": "The Student explained equivalent fractions.",
        "source_message_ids": ["00000000-0000-0000-0000-000000000001"],
        "candidate_event_ids": [],
        "historical_anchor_evidence_ids": [],
        "transfer_context": "not_tested",
        "retention_context": "not_tested",
        "dimensions": {
            "understanding": "demonstrated",
            "independence": "independent",
            "reasoning_demonstration": "coherent",
            "transfer": "not_tested",
            "self_correction": "not_observed",
            "retention": "not_tested",
            "strategy_effectiveness": "not_evaluable",
            "persistence": "not_observed",
            "confidence_calibration": "not_observed",
        },
        "relationship": "supports",
        "reported_broad_subject": None,
        "teaching_method_id": None,
        "teaching_method_source_tutor_message_id": None,
        "misconception_evidence": None,
    }
    finding.update(overrides)
    return finding


def test_v3_finding_omits_legacy_school_alignment_and_requires_unknown_context() -> None:
    """A source-free v3 Review has review-level UNKNOWN context, not legacy fields."""

    source_free = {
        "version": SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
        "segment_kind": "LEARNING",
        "primary_broad_subject": "MATH",
        "school_context": {
            "school_relation": "UNKNOWN",
            "school_subject_ref": None,
            "school_domain_path": [],
            "unit_ref": None,
            "lesson_ref": None,
            "page_refs": [],
            "source_refs": [],
        },
        "findings": [_v3_finding()],
    }

    parsed = SegmentLearningReviewV3Envelope.model_validate(source_free)

    assert parsed.school_context.school_relation == "UNKNOWN"
    assert not hasattr(parsed.findings[0], "school_or_extended")
    assert not hasattr(parsed.findings[0], "subject_alignment")
    with pytest.raises(ValueError):
        SegmentLearningReviewV3Envelope.model_validate({**source_free, "school_context": None})
    with pytest.raises(ValueError):
        SegmentLearningReviewV3Envelope.model_validate(
            {
                **source_free,
                "school_context": {
                    **source_free["school_context"],
                    "school_subject_ref": "invented_subject",
                    "source_refs": ["invented-source"],
                },
            }
        )


def test_live_non_learning_review_accepts_null_school_context() -> None:
    """NON_LEARNING must not be rejected while enforcing Learning-only school sources."""

    review = validate_live_segment_review_output(
        {
            "version": SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
            "segment_kind": "NON_LEARNING",
            "primary_broad_subject": None,
            "school_context": None,
            "findings": [],
        },
        messages=[],
        candidates=[],
    )

    assert review.segment_kind == "NON_LEARNING"


@pytest.mark.parametrize("school_relation", ["UNKNOWN", "SCHOOL_ALIGNED"])
def test_v3_extended_event_requires_extended_review_context(school_relation: str) -> None:
    """An event cannot claim extended learning when its Review says otherwise."""

    context = {
        "school_relation": school_relation,
        "school_subject_ref": None,
        "school_domain_path": [],
        "unit_ref": None,
        "lesson_ref": None,
        "page_refs": [],
        "source_refs": [],
    }
    if school_relation == "SCHOOL_ALIGNED":
        context["source_refs"] = ["trusted:school-outline"]
    with pytest.raises(ValueError):
        SegmentLearningReviewV3Envelope.model_validate(
            {
                "version": SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
                "segment_kind": "LEARNING",
                "primary_broad_subject": "MATH",
                "school_context": context,
                "findings": [_v3_finding(validated_event_type="extended_learning_event")],
            }
        )


def test_v3_extended_event_accepts_extended_context_only_with_trusted_source() -> None:
    """EXTENDED remains source-grounded rather than a source-free fallback."""

    output = {
        "version": SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION,
        "segment_kind": "LEARNING",
        "primary_broad_subject": "MATH",
        "school_context": {
            "school_relation": "EXTENDED",
            "school_subject_ref": None,
            "school_domain_path": [],
            "unit_ref": None,
            "lesson_ref": None,
            "page_refs": [],
            "source_refs": ["trusted:extended-source"],
        },
        "findings": [_v3_finding(validated_event_type="extended_learning_event")],
    }

    parsed = SegmentLearningReviewV3Envelope.model_validate(output)

    assert parsed.school_context is not None
    assert parsed.school_context.school_relation == "EXTENDED"
    source = SimpleNamespace(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        role="student",
        content="I explained an extended learning activity.",
        payload={},
    )
    live = validate_live_segment_review_output(
        output,
        messages=[source],
        candidates=[],
        trusted_school_source_refs=frozenset({"trusted:extended-source"}),
    )
    assert live.school_context is not None
    assert live.school_context.school_relation == "EXTENDED"
    with pytest.raises(SegmentReviewValidationError):
        validate_live_segment_review_output(output, messages=[source], candidates=[])
