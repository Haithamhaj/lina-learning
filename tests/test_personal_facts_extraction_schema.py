"""Provider-schema and boundary tests for Personal Facts extraction."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from services.personal_facts.extraction import (
    PERSONAL_FACTS_SCHEMA_VERSION,
    PersonalFactsExtractionEnvelope,
    extraction_request,
    validate_extraction_output,
)


def _candidate_schema(schema: dict[str, object]) -> dict[str, object]:
    items = schema["properties"]["candidates"]["items"]
    assert isinstance(items, dict)
    reference = items["$ref"]
    assert isinstance(reference, str)
    definition_name = reference.removeprefix("#/$defs/")
    candidate = schema["$defs"][definition_name]
    assert isinstance(candidate, dict)
    return candidate


def _assert_strict_objects_are_complete(schema: object) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            assert schema.get("additionalProperties") is False
            assert set(schema.get("required", [])) == set(schema.get("properties", {}))
        for value in schema.values():
            _assert_strict_objects_are_complete(value)
    elif isinstance(schema, list):
        for value in schema:
            _assert_strict_objects_are_complete(value)


def test_provider_schema_uses_one_strict_complete_candidate_object() -> None:
    schema = PersonalFactsExtractionEnvelope.model_json_schema()
    candidate = _candidate_schema(schema)

    assert schema["type"] == "object"
    assert "oneOf" not in candidate
    _assert_strict_objects_are_complete(schema)


def test_extraction_prompt_requires_canonical_fact_keys() -> None:
    request = extraction_request(
        [],
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4()),
    )
    instructions = str(request["instructions"])

    assert "fact_key must always be lowercase ASCII" in instructions
    assert "PREFERENCE -> preference:" in instructions
    assert "FAVORITE -> favorite:" in instructions
    assert "ACTIVITY -> activity:" in instructions
    assert "PET -> pet:" in instructions
    assert "RELATIONSHIP -> relationship:" in instructions
    assert "SAFE_PERSONAL_CONTEXT -> context:" in instructions
    assert "I like drawing" in instructions
    assert "fact_key=preference:drawing" in instructions
    assert "I have a cat named Mishmish" in instructions
    assert "fact_key=pet:cat" in instructions


@pytest.mark.parametrize(
    "candidate",
    [
        {
            "action": "ADD_NEW",
            "existing_fact_id": str(uuid4()),
            "category": "PREFERENCE",
            "fact_key": "preference:drawing",
            "value": "LIKE",
            "display_statement": "Likes drawing",
        },
        {
            "action": "SUPPORT_EXISTING",
            "existing_fact_id": None,
            "category": "PREFERENCE",
            "fact_key": None,
            "value": None,
            "display_statement": None,
        },
    ],
)
def test_validation_rejects_action_incompatible_provider_candidates_before_source_queries(
    candidate: dict[str, object],
) -> None:
    candidate["supporting_assertions"] = [
        {
            "source_message_id": str(uuid4()),
            "explicit_student_assertion": "I like drawing",
        }
    ]
    envelope = PersonalFactsExtractionEnvelope.model_validate(
        {"version": PERSONAL_FACTS_SCHEMA_VERSION, "candidates": [candidate]}
    )
    student_id = uuid4()
    session = SimpleNamespace(scalars=lambda *_: pytest.fail("invalid candidate must be rejected before source queries"))
    learning_session = SimpleNamespace(id=uuid4(), status="CLOSED", student_id=student_id)

    assert validate_extraction_output(
        session,
        student_id=student_id,
        learning_session=learning_session,
        envelope=envelope,
    ) == []
