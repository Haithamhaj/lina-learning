"""Compact deterministic golden scenarios for the production Tutor orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.platform.db.models import CandidateEvent, LearningMessage, ModelTask
from services.platform.safety import SafetyAction, SafetyDecision
from services.retrieval.service import RetrievedBlock
from services.tutor.context import SessionContextMessage, TutorContext, TutorContextDebug
from services.tutor.runtime import TeachingMode, TeachingStrategy, TutorRuntime, TutorTextDelta, TutorTurn


class _Session:
    def __init__(self) -> None:
        self.rows: list[object] = []

    def add(self, row: object) -> None:
        if isinstance(row, LearningMessage) and row.id is None:
            row.id = uuid4()
        self.rows.append(row)

    def flush(self) -> None:
        return None


class _ContextBuilder:
    def __init__(self) -> None:
        self.calls = 0

    def build(self, *, learning_session: object, question: str) -> TutorContext:
        del learning_session
        self.calls += 1
        message_id = uuid4()
        block = RetrievedBlock(
            text="Equivalent fractions name the same amount.", source_ref="book#page=12", page_number=12,
            block_type="EXERCISE", score=1.0, semantic_key="fractions", semantic_type="EXERCISE",
            concept_key="fractions", source_refs=("book#page=12",), page_numbers=(12,), matched=True,
        )
        return TutorContext(
            question=question, subject="MATH", grade_level=5, focus=None,
            session_messages=(SessionContextMessage(message_id, "student", question),),
            retrieval=(block,), intelligence=(),
            debug=TutorContextDebug(None, (message_id,), ("book#page=12",), (), ()),
        )


class _Policy:
    def __init__(self, decision: SafetyDecision) -> None:
        self.decision = decision

    def evaluate(self, **_: object) -> SafetyDecision:
        return self.decision


class _Provider:
    def __init__(
        self,
        text: str = "Try one small step.",
        candidate_metadata: object | None = None,
        suggested_actions: object | None = None,
        teaching_method_id: object | None = None,
    ) -> None:
        self.calls = 0
        self.payloads: list[dict[str, object]] = []
        self.text = text
        self.candidate_metadata = candidate_metadata
        self.suggested_actions = suggested_actions
        self.teaching_method_id = teaching_method_id

    def stream(self, route: ModelRoute, payload: dict[str, object]):
        del route
        self.calls += 1
        self.payloads.append(payload)
        yield StreamDelta(self.text[:8])
        yield StreamDelta(self.text[8:])
        metadata = self.candidate_metadata(payload) if callable(self.candidate_metadata) else self.candidate_metadata
        output: dict[str, object] = {
            "text": self.text,
            "suggested_actions": self.suggested_actions or [],
            "teaching_method_id": self.teaching_method_id,
            "candidate_metadata": metadata,
        }
        if self.suggested_actions is not None:
            output["suggested_actions"] = self.suggested_actions
        if metadata is not None:
            output["candidate_metadata"] = metadata
        yield StreamComplete(ModelResult(output=output, input_tokens=4, output_tokens=3))


def _decision(action: SafetyAction = SafetyAction.ALLOW, directive: str | None = None) -> SafetyDecision:
    return SafetyDecision(action, None, "BASELINE", 1, f"TEST_{action.value}", "normal", directive)


def _runtime(
    decision: SafetyDecision,
    candidate_metadata: object | None = None,
    suggested_actions: object | None = None,
    teaching_method_id: object | None = None,
) -> tuple[TutorRuntime, _ContextBuilder, _Provider, _Session]:
    session = _Session()
    context = _ContextBuilder()
    provider = _Provider(
        candidate_metadata=candidate_metadata,
        suggested_actions=suggested_actions,
        teaching_method_id=teaching_method_id,
    )
    gateway = ModelGateway(session, routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")}, providers={"fixture": provider})
    return TutorRuntime(session, context_builder=context, safety_policy=_Policy(decision), gateway=gateway), context, provider, session


@pytest.mark.parametrize(
    ("question", "mode", "strategy"),
    [
        ("Explain equivalent fractions.", TeachingMode.LEARN, TeachingStrategy.EXPLAIN_WITH_EXAMPLE),
        ("Help with my homework worksheet without the answer yet.", TeachingMode.HOMEWORK, TeachingStrategy.HINT_FIRST),
        ("I am stuck and do not understand fractions.", TeachingMode.LEARN, TeachingStrategy.EXPLAIN_THEN_CHECK),
        ("I am curious about black holes outside our school topic.", TeachingMode.EXPLORE, TeachingStrategy.EXPLAIN_WITH_EXAMPLE),
        ("Can we review decimals again?", TeachingMode.REVIEW, TeachingStrategy.EXPLAIN_WITH_EXAMPLE),
        ("Quiz me on multiplying by 10.", TeachingMode.QUIZ, TeachingStrategy.EXPLAIN_WITH_EXAMPLE),
        ("ساعدني في واجبي بدون الحل مباشرة.", TeachingMode.HOMEWORK, TeachingStrategy.HINT_FIRST),
        ("Explain الكسور equivalent fractions.", TeachingMode.LEARN, TeachingStrategy.EXPLAIN_WITH_EXAMPLE),
    ],
)
def test_tutor_golden_modes_and_languages_use_one_grounded_stream(
    question: str, mode: TeachingMode, strategy: TeachingStrategy,
) -> None:
    runtime, context, provider, session = _runtime(_decision())
    learning_session = SimpleNamespace(id=uuid4(), student_id=uuid4(), last_activity_at=None)

    events = list(runtime.stream_turn(learning_session=learning_session, question=question))

    turn = events[-1]
    assert isinstance(turn, TutorTurn)
    assert any(isinstance(event, TutorTextDelta) for event in events)
    assert turn.mode is mode
    assert turn.strategy is strategy
    assert turn.sources == [{"source_ref": "book#page=12", "page_number": 12, "block_type": "EXERCISE"}]
    assert context.calls == 1
    assert provider.calls == 1
    assert "Reply primarily in the language" in str(provider.payloads[0]["instructions"])
    assert len([row for row in session.rows if isinstance(row, LearningMessage)]) == 2


def test_current_independence_overrides_support_first_strategy() -> None:
    runtime, _, provider, _ = _runtime(_decision())
    events = list(runtime.stream_turn(learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), last_activity_at=None), question="I solved it myself: 4.5 × 10 = 45."))

    assert isinstance(events[-1], TutorTurn)
    assert events[-1].strategy is TeachingStrategy.INDEPENDENT_CHECK
    assert provider.payloads[0]["strategy"] == TeachingStrategy.INDEPENDENT_CHECK.value


def test_instructional_turn_persists_only_an_eligible_server_validated_method() -> None:
    """Catches a model-selected method being accepted without runtime eligibility validation."""

    runtime, _, provider, session = _runtime(
        _decision(),
        teaching_method_id="CONCRETE_EXAMPLE",
    )

    events = list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question="Explain equivalent fractions.",
    ))

    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert isinstance(events[-1], TutorTurn)
    assert provider.payloads[0]["eligible_teaching_methods"]
    assert tutor_message.payload["teaching_method_id"] == "CONCRETE_EXAMPLE"
    assert tutor_message.payload["teaching_method_registry_version"] == "teaching-method-registry-v1"
    assert not hasattr(events[-1], "teaching_method_id")


def test_ineligible_model_method_is_not_persisted_silently() -> None:
    """Catches a Tutor response claiming a method that runtime did not offer."""

    runtime, _, _, session = _runtime(
        _decision(),
        teaching_method_id="SYMBOLIC_EXPLANATION",
    )

    list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question="Explain equivalent fractions.",
    ))

    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert "teaching_method_id" not in tutor_message.payload
    assert tutor_message.payload["teaching_method_status"] == "ineligible"


def test_instructional_turn_without_a_selected_method_is_auditable() -> None:
    """Catches a missing instructional method being indistinguishable from a non-teaching turn."""

    runtime, _, _, session = _runtime(_decision())

    list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question="Explain equivalent fractions.",
    ))

    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert "teaching_method_id" not in tutor_message.payload
    assert tutor_message.payload["teaching_method_status"] == "missing"


def test_safety_redirect_persists_no_teaching_method() -> None:
    """Catches internal method attribution on a deterministic Safety response."""

    runtime, _, _, session = _runtime(
        _decision(SafetyAction.REDIRECT_TO_PARENT, "Please talk with a trusted grown-up."),
        teaching_method_id="CONCRETE_EXAMPLE",
    )

    list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question="Can you help?",
    ))

    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert "teaching_method_id" not in tutor_message.payload


def test_confusion_excludes_the_latest_valid_persisted_method_from_the_next_turn() -> None:
    """Catches a continued-confusion turn repeating the latest valid method."""

    runtime, _, provider, session = _runtime(_decision(), teaching_method_id="CONCRETE_EXAMPLE")
    learning_session = SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None)
    session.add(LearningMessage(
        session_id=learning_session.id,
        role="tutor",
        content="Let us use the rule.",
        payload={
            "teaching_method_id": "SYMBOLIC_EXPLANATION",
            "teaching_method_registry_version": "teaching-method-registry-v1",
        },
        created_at=datetime.now(UTC) - timedelta(seconds=1),
    ))

    list(runtime.stream_turn(learning_session=learning_session, question="لسه مش فاهمة"))

    assert "SYMBOLIC_EXPLANATION" not in provider.payloads[0]["eligible_teaching_methods"]


def test_explicit_repeat_request_keeps_the_previous_method_eligible() -> None:
    """Catches a direct request to see the same representation again being removed."""

    runtime, _, provider, session = _runtime(_decision(), teaching_method_id="VISUAL_REPRESENTATION")
    learning_session = SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None)
    session.add(LearningMessage(
        session_id=learning_session.id,
        role="tutor",
        content="Imagine a fraction bar.",
        payload={
            "teaching_method_id": "VISUAL_REPRESENTATION",
            "teaching_method_registry_version": "teaching-method-registry-v1",
        },
        created_at=datetime.now(UTC) - timedelta(seconds=1),
    ))

    list(runtime.stream_turn(learning_session=learning_session, question="لسه مش فاهمة، ورجيني بالرسم مرة ثانية"))

    assert "VISUAL_REPRESENTATION" in provider.payloads[0]["eligible_teaching_methods"]


def test_strategy_outcome_receives_only_server_grounded_prior_method_lineage() -> None:
    """Catches a model-supplied outcome being persisted without the actual prior Tutor method."""

    session_holder: dict[str, _Session] = {}

    def metadata(_: dict[str, object]) -> dict[str, object]:
        return _candidate_for_current_message(
            session_holder["session"],
            event_type="strategy_outcome",
            signal="applied_after_concrete_example",
            observed_student_outcome="The Student correctly applied the example.",
        )

    runtime, _, _, session = _runtime(
        _decision(),
        candidate_metadata=metadata,
        teaching_method_id="CONCRETE_EXAMPLE",
    )
    session_holder["session"] = session
    learning_session = SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None)
    prior = LearningMessage(
        session_id=learning_session.id,
        role="tutor",
        content="Use one half of a pizza.",
        payload={
            "teaching_method_id": "CONCRETE_EXAMPLE",
            "teaching_method_registry_version": "teaching-method-registry-v1",
        },
        created_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    session.add(prior)

    list(runtime.stream_turn(
        learning_session=learning_session,
        question="Now I can explain why one half is two fourths.",
    ))

    candidate = next(row for row in session.rows if isinstance(row, CandidateEvent))
    assert candidate.payload["strategy_key"] == "CONCRETE_EXAMPLE"
    assert candidate.payload["strategy_source_tutor_message_id"] == str(prior.id)
    assert candidate.payload["strategy_registry_version"] == "teaching-method-registry-v1"


def test_strategy_outcome_without_valid_prior_method_is_filtered_but_other_candidates_survive() -> None:
    """Catches an ungrounded strategy outcome reaching Evidence or dropping another valid Candidate."""

    session_holder: dict[str, _Session] = {}

    def metadata(_: dict[str, object]) -> dict[str, object]:
        source_id = next(
            row.id for row in session_holder["session"].rows
            if isinstance(row, LearningMessage) and row.role == "student"
        )
        return {
            "version": "candidate-event-v1",
            "candidates": [
                {
                    "event_type": "strategy_outcome",
                    "concept_ref": "equivalent_fractions",
                    "summary": "The Student responded after a method.",
                    "signal": "outcome_without_lineage",
                    "source_message_ids": [str(source_id)],
                    "school_or_extended": "school",
                    "observed_student_outcome": "The Student made a meaningful attempt.",
                },
                {
                    "event_type": "learning_attempt",
                    "concept_ref": "equivalent_fractions",
                    "summary": "The Student made a meaningful attempt.",
                    "signal": "fraction_attempt",
                    "source_message_ids": [str(source_id)],
                    "school_or_extended": "school",
                    "observed_student_outcome": None,
                },
            ],
        }

    runtime, _, _, session = _runtime(_decision(), candidate_metadata=metadata)
    session_holder["session"] = session
    learning_session = SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None)

    list(runtime.stream_turn(learning_session=learning_session, question="I tried one half and two fourths."))

    candidates = [row for row in session.rows if isinstance(row, CandidateEvent)]
    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert [candidate.event_type for candidate in candidates] == ["learning_attempt"]
    assert tutor_message.payload["candidate_metadata_status"] == "strategy_outcome_lineage_missing"


def test_completed_turn_preserves_only_four_trimmed_typed_suggested_actions() -> None:
    """Catches a completed structured turn leaking malformed actions into persistence or the Student API."""

    runtime, _, _, session = _runtime(
        _decision(),
        suggested_actions=[
            {"label": " خليني أجرب ✍️ ", "kind": "NAVIGATION"},
            {"label": "", "kind": "NAVIGATION"},
            {"label": "candidate_metadata: {source_message_ids}", "kind": "NAVIGATION"},
            {"label": "مثال ثاني 🍕", "kind": "NAVIGATION"},
            {"label": "فهمت 👍", "kind": "NAVIGATION"},
            {"label": "اشرحها بطريقة ثانية", "kind": "NAVIGATION"},
            {"label": "2/4", "kind": "ANSWER_CHOICE"},
        ],
    )

    events = list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), last_activity_at=None),
        question="Explain equivalent fractions.",
    ))

    turn = events[-1]
    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert isinstance(turn, TutorTurn)
    assert [action.model_dump() for action in turn.suggested_actions] == [
        {"label": "خليني أجرب ✍️", "kind": "NAVIGATION"},
        {"label": "مثال ثاني 🍕", "kind": "NAVIGATION"},
        {"label": "فهمت 👍", "kind": "NAVIGATION"},
        {"label": "اشرحها بطريقة ثانية", "kind": "NAVIGATION"},
    ]
    assert tutor_message.payload["suggested_actions"] == [action.model_dump() for action in turn.suggested_actions]


@pytest.mark.parametrize("action", [SafetyAction.REDIRECT_TO_PARENT, SafetyAction.BLOCK])
def test_redirect_and_protected_actions_persist_policy_response_without_a_model_call(action: SafetyAction) -> None:
    runtime, context, provider, session = _runtime(_decision(action, "Please talk with a trusted grown-up."))

    events = list(runtime.stream_turn(learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), last_activity_at=None), question="Can you help?"))

    assert isinstance(events[-1], TutorTurn)
    assert events[-1].text == "Please talk with a trusted grown-up."
    assert context.calls == 0
    assert provider.calls == 0
    assert len([row for row in session.rows if isinstance(row, LearningMessage)]) == 2
    assert events[-1].suggested_actions == []


def test_age_appropriate_turn_continues_with_the_policy_directive() -> None:
    runtime, _, provider, _ = _runtime(_decision(SafetyAction.AGE_APPROPRIATE_ONLY, "Use simple child-safe framing."))

    list(runtime.stream_turn(learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), last_activity_at=None), question="Can you explain this family topic?"))

    assert "Use simple child-safe framing." in str(provider.payloads[0]["input"])


def test_interrupted_stream_drains_provider_and_persists_the_final_tutor_response() -> None:
    runtime, _, provider, session = _runtime(_decision())
    stream = runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), last_activity_at=None),
        question="Explain equivalent fractions.",
    )

    assert isinstance(next(stream), TutorTextDelta)
    stream.close()

    messages = [row for row in session.rows if isinstance(row, LearningMessage)]
    assert provider.calls == 1
    assert [message.role for message in messages] == ["student", "tutor"]
    assert messages[-1].content == "Try one small step."


def _candidate_for_current_message(
    session: _Session,
    *,
    event_type: str,
    signal: str,
    observed_student_outcome: str | None = None,
) -> dict[str, object]:
    student_message = next(
        row for row in session.rows if isinstance(row, LearningMessage) and row.role == "student"
    )
    candidate: dict[str, object] = {
        "version": "candidate-event-v1",
        "candidates": [{
            "event_type": event_type,
            "concept_ref": "equivalent_fractions",
            "summary": "The Student made a meaningful fraction-learning contribution.",
            "signal": signal,
            "source_message_ids": [str(student_message.id)],
            "school_or_extended": "school",
        }],
    }
    if observed_student_outcome is not None:
        candidate["candidates"][0]["observed_student_outcome"] = observed_student_outcome
    return candidate


@pytest.mark.parametrize("question", ["Hello Lina!", "Thank you for helping me."])
def test_greeting_and_thanks_record_candidate_metadata_absence(question: str) -> None:
    runtime, _, _, session = _runtime(_decision())

    list(runtime.stream_turn(learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), last_activity_at=None), question=question))

    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert not [row for row in session.rows if isinstance(row, CandidateEvent)]
    assert tutor_message.payload["candidate_metadata_status"] == "absent"


@pytest.mark.parametrize(
    ("event_type", "signal", "outcome"),
    [
        ("independent_success", "solved_independently", None),
        ("guided_success", "completed_after_light_hint", None),
        ("misconception_signal", "treated_numerators_and_denominators_as_separate_values", None),
        ("self_correction", "corrected_fraction_comparison", None),
        ("explanation_attempt", "explained_equivalent_fraction_reasoning", None),
        ("transfer_attempt", "applied_fraction_equivalence_to_a_recipe", None),
        ("open_loop_created", "explicitly_stuck_without_outcome", None),
    ],
)
def test_valid_same_call_candidate_metadata_is_persisted_with_raw_source_linkage(
    event_type: str, signal: str, outcome: str | None,
) -> None:
    session_holder: dict[str, _Session] = {}

    def metadata(_: dict[str, object]) -> dict[str, object]:
        return _candidate_for_current_message(session_holder["session"], event_type=event_type, signal=signal, observed_student_outcome=outcome)

    runtime, _, provider, session = _runtime(_decision(), metadata)
    session_holder["session"] = session
    list(runtime.stream_turn(learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None), question="I worked out why one half equals two fourths."))

    candidate = next(row for row in session.rows if isinstance(row, CandidateEvent))
    student_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "student")
    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert provider.calls == 1
    assert candidate.session_id == student_message.session_id
    assert candidate.message_id == student_message.id
    assert candidate.event_type == event_type
    assert candidate.payload["subject"] == "MATH"
    assert candidate.payload["source_message_ids"] == [str(student_message.id)]
    assert tutor_message.payload["candidate_metadata_status"] == "persisted"


@pytest.mark.parametrize(
    ("question", "suggested_action_kind"),
    [
        ("I got it", None),
        ("فهمت 👍", None),
        ("Let me try ✍️", "NAVIGATION"),
    ],
)
def test_self_reports_and_suggested_action_clicks_never_persist_mastery_candidate_metadata(
    question: str, suggested_action_kind: str | None,
) -> None:
    """Catches a self-report or action selection being promoted to Candidate/Evidence despite no observed work."""

    session_holder: dict[str, _Session] = {}

    def metadata(_: dict[str, object]) -> dict[str, object]:
        return _candidate_for_current_message(
            session_holder["session"],
            event_type="independent_success",
            signal="solved_independently",
        )

    runtime, _, provider, session = _runtime(_decision(), metadata)
    session_holder["session"] = session
    list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question=question,
        suggested_action_kind=suggested_action_kind,
    ))

    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert provider.calls == 1
    assert not [row for row in session.rows if isinstance(row, CandidateEvent)]
    assert tutor_message.payload["candidate_metadata_status"] == "not_evidence"


def test_answer_choice_can_persist_a_bounded_attempt_but_not_independent_success() -> None:
    """Catches a guided choice becoming an independent/mastery claim while preserving its observable attempt value."""

    session_holder: dict[str, _Session] = {}

    def metadata(_: dict[str, object]) -> dict[str, object]:
        return _candidate_for_current_message(
            session_holder["session"],
            event_type="learning_attempt",
            signal="selected_equivalent_fraction_choice",
        )

    runtime, _, _, session = _runtime(_decision(), metadata)
    session_holder["session"] = session
    list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question="2/4",
        suggested_action_kind="ANSWER_CHOICE",
    ))

    candidate = next(row for row in session.rows if isinstance(row, CandidateEvent))
    student_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "student")
    assert candidate.event_type == "learning_attempt"
    assert student_message.payload["input_kind"] == "suggested_action_answer_choice"


def test_answer_choice_never_persists_independent_success_from_the_click_alone() -> None:
    """Catches the model upgrading one button choice to independent evidence."""

    session_holder: dict[str, _Session] = {}

    def metadata(_: dict[str, object]) -> dict[str, object]:
        return _candidate_for_current_message(
            session_holder["session"],
            event_type="independent_success",
            signal="solved_independently",
        )

    runtime, _, _, session = _runtime(_decision(), metadata)
    session_holder["session"] = session
    list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question="2/4",
        suggested_action_kind="ANSWER_CHOICE",
    ))

    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert not [row for row in session.rows if isinstance(row, CandidateEvent)]
    assert tutor_message.payload["candidate_metadata_status"] == "answer_choice_filtered"


@pytest.mark.parametrize(
    "candidate_metadata",
    [
        {"version": "candidate-event-v1", "candidates": [{"event_type": "not_a_real_event"}]},
        {"version": "candidate-event-v1", "candidates": [{"event_type": "strategy_outcome", "summary": "Tutor used an example."}]},
    ],
)
def test_malformed_candidate_metadata_never_breaks_the_tutor_response(candidate_metadata: dict[str, object]) -> None:
    runtime, _, provider, session = _runtime(_decision(), candidate_metadata)

    events = list(runtime.stream_turn(learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), last_activity_at=None), question="I am stuck with fractions."))

    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert events[-1].text == "Try one small step."
    assert provider.calls == 1
    assert not [row for row in session.rows if isinstance(row, CandidateEvent)]
    assert tutor_message.payload["candidate_metadata_status"] == "invalid"
