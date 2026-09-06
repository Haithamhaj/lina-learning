from __future__ import annotations

from services.studio.subjects.contracts import ValidationStatus
import pytest


@pytest.mark.parametrize("token", [[], {}, None, 7])
def test_arabic_malformed_token_types_fail_with_validation_error(token):
    from services.studio.subjects.arabic_sentence_ordering import validate_reorder_payload
    with pytest.raises(ValueError):
        validate_reorder_payload({"token_id": token, "from_index": 0, "to_index": 1})


def test_arabic_sentence_ordering_seed_is_opaque_noncanonical_and_server_validated() -> None:
    """The browser-safe seed must not carry the constrained Arabic answer order."""

    from services.studio.subjects.arabic_sentence_ordering import (
        ACTIVITY_KEY,
        LESSON_TOKEN_ID,
        STUDENT_TOKEN_ID,
        VERB_TOKEN_ID,
        arabic_sentence_ordering_scene_seed,
        validate_submit_configuration,
    )

    seed = arabic_sentence_ordering_scene_seed()
    assert seed["token_ids"] == [STUDENT_TOKEN_ID, LESSON_TOKEN_ID, VERB_TOKEN_ID]
    assert [token["id"] for token in seed["tokens"]] != [VERB_TOKEN_ID, STUDENT_TOKEN_ID, LESSON_TOKEN_ID]
    assert not any("answer" in key or "valid" in key for key in seed)

    valid = validate_submit_configuration({
        "action": {"token_ids": [VERB_TOKEN_ID, STUDENT_TOKEN_ID, LESSON_TOKEN_ID]},
        "activity_state": {ACTIVITY_KEY: {"token_ids": [VERB_TOKEN_ID, STUDENT_TOKEN_ID, LESSON_TOKEN_ID]}},
    })
    wrong = validate_submit_configuration({
        "action": {"token_ids": [STUDENT_TOKEN_ID, LESSON_TOKEN_ID, VERB_TOKEN_ID]},
        "activity_state": {"scene_seed": seed},
    })
    assert valid.status is ValidationStatus.VALID
    assert wrong.status is ValidationStatus.INVALID


def test_arabic_v2_profile_extends_without_reinterpreting_arabic_v1() -> None:
    from services.studio.subjects import production_subject_registry
    from services.studio.subjects.arabic_sentence_ordering import ACTIVITY_KEY, ARABIC_PROFILE_VERSION

    registry = production_subject_registry()
    assert registry.resolve_profile("ARABIC", "subject-profile-v1").activities == ()
    assert registry.resolve_profile("ARABIC", ARABIC_PROFILE_VERSION).activities[0].activity_key == ACTIVITY_KEY


def test_instruction_also_allows_verb_object_subject_with_supplied_case_endings():
    from services.studio.subjects.arabic_sentence_ordering import ACTIVITY_KEY, VERB_TOKEN_ID, STUDENT_TOKEN_ID, LESSON_TOKEN_ID, validate_submit_configuration
    order = [VERB_TOKEN_ID, LESSON_TOKEN_ID, STUDENT_TOKEN_ID]
    assert validate_submit_configuration({"action":{"token_ids":order},"activity_state":{ACTIVITY_KEY:{"token_ids":order}}}).status is ValidationStatus.VALID


def test_arabic_active_scene_reuse_requires_exact_payload_schema():
    from types import SimpleNamespace
    from services.studio.arabic_sentence_ordering_activation import _is_scene
    from services.studio.subjects import arabic_sentence_ordering as a
    scene=SimpleNamespace(subject_key="ARABIC",subject_profile_version=a.ARABIC_PROFILE_VERSION,activity_key=a.ACTIVITY_KEY,activity_contract_version=a.ACTIVITY_VERSION,renderer_key=a.RENDERER_KEY,renderer_version=a.RENDERER_VERSION,payload_schema_version="unknown")
    assert not _is_scene(scene)
