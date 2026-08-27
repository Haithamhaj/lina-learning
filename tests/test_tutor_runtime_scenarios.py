"""Compact deterministic golden scenarios for the production Tutor orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta, StreamParentBoundaryDecision
from services.platform.db.models import CandidateEvent, LearningMessage, ModelTask
from services.platform.safety import ParentBoundaryResolution, SafetyAction, SafetyDecision
from services.retrieval.service import RetrievedBlock
from services.tutor.context import SessionContextMessage, TutorContext, TutorContextDebug
from services.tutor.capacity import TutorContextCapacityExceeded
from services.tutor.runtime import TutorRuntime, TutorTextDelta, TutorTurn, _compose_parent_redirect
from services.tutor.teaching_decisions import PriorMethodRelation, TeachingMode, TeachingStrategy
from services.tutor.parent_boundaries import (
    PARENT_BOUNDARY_SCHEMA_VERSION,
    ParentBoundaryCategory,
    ParentBoundaryDecision,
    ParentBoundaryModelAction,
)


class _Session:
    def __init__(self) -> None:
        self.rows: list[object] = []

    def add(self, row: object) -> None:
        if isinstance(row, LearningMessage) and row.id is None:
            row.id = uuid4()
        self.rows.append(row)

    def flush(self) -> None:
        return None

    def get(self, entity: type[object], identifier: object) -> object | None:
        return next(
            (
                row
                for row in self.rows
                if isinstance(row, entity) and getattr(row, "id", None) == identifier
            ),
            None,
        )


class _ContextBuilder:
    def __init__(self) -> None:
        self.calls = 0

    def build(
        self,
        *,
        learning_session: object,
        question: str,
        current_turn_message_id: object | None = None,
    ) -> TutorContext:
        del learning_session
        self.calls += 1
        message_id = current_turn_message_id if current_turn_message_id is not None else uuid4()
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
        guided_check: object | None = None,
        teaching_method_id: object | None = None,
        teaching_mode: object | None = None,
        teaching_strategy: object | None = None,
        prior_method_relation: object | None = None,
    ) -> None:
        self.calls = 0
        self.payloads: list[dict[str, object]] = []
        self.text = text
        self.candidate_metadata = candidate_metadata
        self.suggested_actions = suggested_actions
        self.guided_check = guided_check
        self.teaching_method_id = teaching_method_id
        self.teaching_mode = teaching_mode
        self.teaching_strategy = teaching_strategy
        self.prior_method_relation = prior_method_relation

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
            "guided_check": self.guided_check,
            "teaching_method_id": self.teaching_method_id,
            "teaching_mode": self.teaching_mode,
            "teaching_strategy": self.teaching_strategy,
            "prior_method_relation": self.prior_method_relation,
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
    guided_check: object | None = None,
    teaching_method_id: object | None = None,
    teaching_mode: object | None = None,
    teaching_strategy: object | None = None,
    prior_method_relation: object | None = None,
) -> tuple[TutorRuntime, _ContextBuilder, _Provider, _Session]:
    session = _Session()
    context = _ContextBuilder()
    provider = _Provider(
        candidate_metadata=candidate_metadata,
        suggested_actions=suggested_actions,
        guided_check=guided_check,
        teaching_method_id=teaching_method_id,
        teaching_mode=teaching_mode,
        teaching_strategy=teaching_strategy,
        prior_method_relation=prior_method_relation,
    )
    gateway = ModelGateway(session, routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")}, providers={"fixture": provider})
    return TutorRuntime(session, context_builder=context, safety_policy=_Policy(decision), gateway=gateway), context, provider, session


def test_arbitrary_literal_message_persists_luna_semantic_decision_without_runtime_keyword_routing() -> None:
    """An opaque message proves the fixture's model decision, rather than words, is authoritative."""

    runtime, context, provider, session = _runtime(
        _decision(),
        teaching_mode="HOMEWORK",
        teaching_strategy="HINT_FIRST",
        teaching_method_id="SOCRATIC_FOCUS",
        prior_method_relation="NOT_RELEVANT",
    )
    learning_session = SimpleNamespace(id=uuid4(), student_id=uuid4(), last_activity_at=None)

    events = list(runtime.stream_turn(learning_session=learning_session, question="violet trapezoid lunar bicycle"))

    turn = events[-1]
    tutor_message = [row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor"][-1]
    assert isinstance(turn, TutorTurn)
    assert any(isinstance(event, TutorTextDelta) for event in events)
    assert turn.mode is TeachingMode.HOMEWORK
    assert turn.strategy is TeachingStrategy.HINT_FIRST
    assert tutor_message.payload["teaching_method_id"] == "SOCRATIC_FOCUS"
    assert tutor_message.payload["prior_method_relation"] is None
    assert tutor_message.payload["teaching_decision_status"] == "prior_method_relation_without_prior"
    assert turn.sources == [{"source_ref": "book#page=12", "page_number": 12, "block_type": "EXERCISE"}]
    assert context.calls == 1
    assert provider.calls == 1
    assert "Reply primarily in the language" in str(provider.payloads[0]["instructions"])
    assert provider.payloads[0]["active_teaching_methods"] == [
        "CONCRETE_EXAMPLE", "VISUAL_REPRESENTATION", "WORKED_EXAMPLE", "SOCRATIC_FOCUS",
        "DECOMPOSITION", "ANALOGY", "SYMBOLIC_EXPLANATION",
    ]
    assert len([row for row in session.rows if isinstance(row, LearningMessage)]) == 2


def test_allow_turn_sends_situational_safety_guidance_in_its_one_tutor_call() -> None:
    """SAFE-01: ALLOW permits one Tutor call; Luna still gets situational-safety guidance."""

    runtime, _, provider, _ = _runtime(_decision(SafetyAction.ALLOW))

    events = list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question="I am doing an activity now.",
    ))

    assert isinstance(events[-1], TutorTurn)
    assert events[-1].safety["action"] == SafetyAction.ALLOW.value
    assert provider.calls == 1
    assert "immediate real-world safety" in str(provider.payloads[0]["instructions"])


def test_protected_context_capacity_overflow_skips_the_primary_model_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches a pre-Luna overflow that still starts streaming or fabricates a Tutor reply."""

    runtime, _, provider, session = _runtime(_decision())
    monkeypatch.setattr(
        "services.tutor.runtime.get_settings",
        lambda: SimpleNamespace(tutor_context_capacity=1, tutor_max_output_tokens=2000),
    )

    with pytest.raises(TutorContextCapacityExceeded):
        list(runtime.stream_turn(
            learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
            question="Explain equivalent fractions.",
        ))

    assert provider.calls == 0
    assert [row.role for row in session.rows if isinstance(row, LearningMessage)] == ["student"]


def test_successful_tutor_turn_persists_private_capacity_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches lost capacity audit data or raw prompt text being persisted as lineage."""

    runtime, _, provider, session = _runtime(_decision())
    monkeypatch.setattr(
        "services.tutor.runtime.get_settings",
        lambda: SimpleNamespace(tutor_context_capacity=1_000_000, tutor_max_output_tokens=2000),
    )

    list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question="Explain equivalent fractions.",
    ))

    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    capacity = tutor_message.payload["context_capacity"]
    assert provider.calls == 1
    assert capacity["capacity_policy_version"] == "tutor-context-capacity-v1"
    assert capacity["initial_measured_size"] == capacity["final_measured_size"]
    assert "Equivalent fractions name the same amount." not in str(capacity)
    assert "Explain equivalent fractions." not in str(capacity)


def test_all_null_luna_decision_persists_no_fictional_teaching_classification() -> None:
    runtime, _, provider, session = _runtime(_decision())
    events = list(runtime.stream_turn(learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), last_activity_at=None), question="Thanks for being here."))

    assert isinstance(events[-1], TutorTurn)
    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert events[-1].mode is None
    assert events[-1].strategy is None
    assert tutor_message.payload["teaching_mode"] is None
    assert tutor_message.payload["teaching_strategy"] is None
    assert tutor_message.payload["teaching_method_id"] is None
    assert tutor_message.payload["prior_method_relation"] is None
    assert provider.calls == 1


def test_valid_luna_method_persists_without_runtime_method_preselection() -> None:

    runtime, _, provider, session = _runtime(
        _decision(),
        teaching_mode="LEARN",
        teaching_strategy="EXPLAIN_WITH_EXAMPLE",
        teaching_method_id="CONCRETE_EXAMPLE",
    )

    events = list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question="Explain equivalent fractions.",
    ))

    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert isinstance(events[-1], TutorTurn)
    assert "eligible_teaching_methods" not in provider.payloads[0]
    assert tutor_message.payload["teaching_method_id"] == "CONCRETE_EXAMPLE"
    assert tutor_message.payload["teaching_method_registry_version"] == "teaching-method-registry-v1"
    assert not hasattr(events[-1], "teaching_method_id")


def test_unknown_luna_method_is_not_persisted_silently() -> None:

    runtime, _, _, session = _runtime(
        _decision(),
        teaching_mode="LEARN",
        teaching_strategy="EXPLAIN_WITH_EXAMPLE",
        teaching_method_id="NOT_A_METHOD",
    )

    list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question="Explain equivalent fractions.",
    ))

    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert tutor_message.payload["teaching_method_id"] is None
    assert tutor_message.payload["teaching_method_status"] == "invalid"


def test_mode_and_strategy_without_a_method_are_valid_and_auditable() -> None:

    runtime, _, _, session = _runtime(_decision(), teaching_mode="LEARN", teaching_strategy="EXPLAIN_WITH_EXAMPLE")

    list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question="Explain equivalent fractions.",
    ))

    tutor_message = [row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor"][-1]
    assert tutor_message.payload["teaching_method_id"] is None
    assert tutor_message.payload["teaching_mode"] == "LEARN"


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

    tutor_message = [row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor"][-1]
    assert tutor_message.payload["teaching_mode"] is None
    assert tutor_message.payload["teaching_strategy"] is None
    assert tutor_message.payload["teaching_method_id"] is None
    assert tutor_message.payload["prior_method_relation"] is None


def test_did_not_help_same_method_is_marked_inconsistent_without_erasing_valid_method_identity() -> None:
    """Only Luna understands the natural message; runtime checks its declared relation."""

    runtime, _, provider, session = _runtime(
        _decision(), teaching_mode="LEARN", teaching_strategy="EXPLAIN_THEN_CHECK",
        teaching_method_id="SYMBOLIC_EXPLANATION", prior_method_relation="DID_NOT_HELP",
    )
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

    list(runtime.stream_turn(learning_session=learning_session, question="second response unrelated literal"))

    tutor_message = [row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor"][-1]
    assert tutor_message.payload["teaching_method_id"] == "SYMBOLIC_EXPLANATION"
    assert tutor_message.payload["prior_method_relation"] is None
    assert tutor_message.payload["teaching_decision_status"] == "prior_method_relation_inconsistent"


def test_explicit_repeat_request_same_method_is_accepted_from_luna() -> None:

    runtime, _, provider, session = _runtime(
        _decision(), teaching_mode="LEARN", teaching_strategy="EXPLAIN_WITH_EXAMPLE",
        teaching_method_id="VISUAL_REPRESENTATION", prior_method_relation="EXPLICIT_REPEAT_REQUEST",
    )
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

    list(runtime.stream_turn(learning_session=learning_session, question="please reproduce that visual explanation"))

    tutor_message = [row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor"][-1]
    assert tutor_message.payload["teaching_method_id"] == "VISUAL_REPRESENTATION"
    assert tutor_message.payload["prior_method_relation"] == "EXPLICIT_REPEAT_REQUEST"


def test_relation_without_a_valid_immediate_prior_method_is_not_persisted() -> None:
    runtime, _, _, session = _runtime(
        _decision(), teaching_mode="LEARN", teaching_strategy="EXPLAIN_WITH_EXAMPLE",
        teaching_method_id="CONCRETE_EXAMPLE", prior_method_relation="HELPED",
    )

    list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question="any non-keyword literal",
    ))

    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert tutor_message.payload["prior_method_relation"] is None
    assert tutor_message.payload["teaching_decision_status"] == "prior_method_relation_without_prior"


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


def test_valid_model_guided_check_receives_a_server_generated_persisted_identity() -> None:
    """ACT-02: Luna proposes only check content; the application owns durable check identity."""

    runtime, _, _, session = _runtime(
        _decision(),
        guided_check={
            "prompt": "6 ÷ 2 = ?",
            "choices": [{"label": "A) 2"}, {"label": "B) 3"}, {"label": "C) 4"}],
        },
    )

    turn = list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None),
        question="Can we try one?",
    ))[-1]

    tutor_message = [row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor"][-1]
    assert isinstance(turn, TutorTurn)
    assert turn.guided_check is not None
    assert turn.guided_check.prompt == "6 ÷ 2 = ?"
    assert [choice.label for choice in turn.guided_check.choices] == ["A) 2", "B) 3", "C) 4"]
    assert tutor_message.payload["guided_check"] == turn.guided_check.model_dump(mode="json")


@pytest.mark.parametrize(
    ("question", "suggested_action_kind", "expected_input_kind"),
    [
        ("Show another example", "NAVIGATION", "suggested_action"),
        ("B) 3", "ANSWER_CHOICE", "suggested_action"),
    ],
)
def test_suggested_action_source_is_persisted_and_sent_to_the_one_tutor_call_outside_recent_context(
    question: str,
    suggested_action_kind: str,
    expected_input_kind: str,
) -> None:
    """ACT-01: selected-action meaning must not rely on the bounded recent-message window."""

    runtime, _, provider, session = _runtime(_decision())
    learning_session = SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None)
    source_message = LearningMessage(
        session_id=learning_session.id,
        role="tutor",
        content="Question 1: 6 stickers are shared equally between 2 children. How many each? A) 2 B) 3 C) 4",
        payload={"suggested_actions": [{"label": question, "kind": suggested_action_kind}]},
        created_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    session.add(source_message)

    list(runtime.stream_turn(
        learning_session=learning_session,
        question=question,
        suggested_action_kind=suggested_action_kind,
        suggested_action_source_tutor_message_id=source_message.id,
    ))

    student_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "student")
    model_input = str(provider.payloads[0]["input"])
    assert provider.calls == 1
    assert student_message.payload["input_kind"] == expected_input_kind
    assert student_message.payload["suggested_action_source_tutor_message_id"] == str(source_message.id)
    assert f"Student question:\n{question}" in model_input
    assert source_message.content in model_input
    assert str(source_message.id) in model_input


def test_suggested_action_source_cannot_be_loaded_from_another_session() -> None:
    runtime, context, provider, session = _runtime(_decision())
    learning_session = SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None)
    foreign_source = LearningMessage(
        session_id=uuid4(),
        role="tutor",
        content="Foreign Tutor question.",
        payload={"suggested_actions": [{"label": "B) 3", "kind": "ANSWER_CHOICE"}]},
    )
    session.add(foreign_source)

    with pytest.raises(ValueError, match="source"):
        list(runtime.stream_turn(
            learning_session=learning_session,
            question="B) 3",
            suggested_action_kind="ANSWER_CHOICE",
            suggested_action_source_tutor_message_id=foreign_source.id,
        ))

    assert context.calls == 0
    assert provider.calls == 0
    assert not [row for row in session.rows if isinstance(row, LearningMessage) and row.role == "student"]


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


class _SemanticPolicy(_Policy):
    def effective_parent_boundaries(self, **_: object) -> dict[str, str]:
        return {"RELIGION": "REDIRECT_TO_PARENT"}

    def resolve_parent_boundary(
        self,
        *,
        decision: ParentBoundaryDecision | None,
        **_: object,
    ) -> ParentBoundaryResolution:
        if decision is not None and decision.applies and decision.category is ParentBoundaryCategory.RELIGION:
            return ParentBoundaryResolution(
                action=SafetyAction.REDIRECT_TO_PARENT,
                category=ParentBoundaryCategory.RELIGION,
                policy_source="DEFAULT_BOUNDARY",
                policy_version=1,
                reason_code="SEMANTIC_TOPIC_REDIRECT_TO_PARENT",
                boundary_state=None,
            )
        return ParentBoundaryResolution(
            action=SafetyAction.ALLOW,
            category=None,
            policy_source="DEFAULT_OPEN",
            policy_version=1,
            reason_code="SEMANTIC_NOT_APPLICABLE",
            boundary_state=None,
        )


class _DecisionFirstProvider:
    def __init__(self, *, applies: bool) -> None:
        self.calls = 0
        self.applies = applies

    def stream(self, route: ModelRoute, payload: dict[str, object]):
        del route, payload
        self.calls += 1
        ordinary = "ORDINARY MODEL TEXT MUST NOT LEAK"
        decision = {
            "schema_version": PARENT_BOUNDARY_SCHEMA_VERSION,
            "category": "RELIGION" if self.applies else None,
            "applies": self.applies,
            "model_action": "REDIRECT_TO_PARENT" if self.applies else "ALLOW",
            "redirect": (
                {
                    "acknowledgement": "أفهم سؤالك.",
                    "parent_reference": "الأفضل أن تتحدثي مع أحد والديك.",
                    "safe_offer": "أستطيع مساعدتك في سؤال دراسي آخر.",
                }
                if self.applies
                else None
            ),
        }
        yield StreamDelta(ordinary[:12])
        yield StreamParentBoundaryDecision(decision)
        yield StreamDelta(ordinary[12:])
        yield StreamComplete(ModelResult(output={
            "text": ordinary,
            "suggested_actions": [],
            "teaching_method_id": None,
            "teaching_mode": None,
            "teaching_strategy": None,
            "prior_method_relation": None,
            "segment_relation": None,
            "structured_segment_state": None,
            "parent_boundary": decision,
            "candidate_metadata": {"version": "candidate-event-v1", "candidates": []},
        }))


def _semantic_runtime(*, applies: bool) -> tuple[TutorRuntime, _DecisionFirstProvider, _Session]:
    session = _Session()
    provider = _DecisionFirstProvider(applies=applies)
    runtime = TutorRuntime(
        session,
        context_builder=_ContextBuilder(),
        safety_policy=_SemanticPolicy(_decision()),
        gateway=ModelGateway(
            session,
            routes={ModelTask.TUTOR: ModelRoute("fixture", "safe02")},
            providers={"fixture": provider},
        ),
    )
    return runtime, provider, session


def test_parent_redirect_discards_all_ordinary_stream_text_and_persists_only_server_composed_reply() -> None:
    """SAFE-02 L/M/N/O/P/Q: no provider text becomes visible or durable on redirect."""

    runtime, provider, session = _semantic_runtime(applies=True)
    question = "هل الله موجود؟"
    events = list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), last_activity_at=None),
        question=question,
    ))

    assert not [event for event in events if isinstance(event, TutorTextDelta)]
    turn = events[-1]
    assert isinstance(turn, TutorTurn)
    assert turn.text == "أفهم سؤالك. الأفضل أن تتحدثي مع أحد والديك. أستطيع مساعدتك في سؤال دراسي آخر."
    messages = [row for row in session.rows if isinstance(row, LearningMessage)]
    assert [message.content for message in messages] == [question, turn.text]
    assert "ORDINARY MODEL TEXT" not in messages[-1].content
    assert messages[-1].payload["candidate_metadata_status"] == "parent_boundary_redirect"
    assert messages[-1].payload["parent_boundary"] == {
        "semantic_category": "RELIGION",
        "applies": True,
        "model_action": "REDIRECT_TO_PARENT",
        "effective_action": "REDIRECT_TO_PARENT",
        "boundary_source": "DEFAULT_BOUNDARY",
        "reason_code": "SEMANTIC_TOPIC_REDIRECT_TO_PARENT",
        "policy_version": 1,
        "enforced": True,
        "response_origin": "server_composed_redirect",
    }
    assert provider.calls == 1


def test_allow_releases_buffered_text_and_persists_complete_parent_boundary_audit() -> None:
    """SAFE-02 streaming guard preserves ALLOW streaming after the decision arrives."""

    runtime, provider, session = _semantic_runtime(applies=False)
    events = list(runtime.stream_turn(
        learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), last_activity_at=None),
        question="Why does air cool at high altitude?",
    ))

    assert [event.text for event in events if isinstance(event, TutorTextDelta)] == [
        "ORDINARY MOD", "EL TEXT MUST NOT LEAK",
    ]
    assert isinstance(events[-1], TutorTurn)
    assert events[-1].text == "ORDINARY MODEL TEXT MUST NOT LEAK"
    tutor_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor")
    assert tutor_message.payload["parent_boundary"] == {
        "semantic_category": None,
        "applies": False,
        "model_action": "ALLOW",
        "effective_action": "ALLOW",
        "boundary_source": "DEFAULT_OPEN",
        "reason_code": "SEMANTIC_NOT_APPLICABLE",
        "policy_version": 1,
        "enforced": False,
        "response_origin": "model_text",
    }
    assert provider.calls == 1


def test_invalid_redirect_fragments_use_the_deterministic_server_fallback() -> None:
    """SAFE-02 R: a fragment defect cannot make a redirect turn fail or expose model text."""

    text, origin = _compose_parent_redirect(
        question="هل الله موجود؟",
        decision=ParentBoundaryDecision(
            schema_version=PARENT_BOUNDARY_SCHEMA_VERSION,
            category=ParentBoundaryCategory.RELIGION,
            applies=True,
            model_action=ParentBoundaryModelAction.REDIRECT_TO_PARENT,
            redirect={
                "acknowledgement": "x" * 161,
                "parent_reference": "راجعي أحد والديك.",
                "safe_offer": "يمكننا الانتقال إلى سؤال دراسي.",
            },
        ),
    )

    assert origin == "server_fallback_redirect"
    assert text == "هذا موضوع يناسب الحديث عنه مع أحد والديك. أستطيع مساعدتك في سؤال دراسي آخر."


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
    student_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "student")
    assert provider.calls == 1
    assert not [row for row in session.rows if isinstance(row, CandidateEvent)]
    assert tutor_message.payload["candidate_metadata_status"] == "not_evidence"
    if suggested_action_kind is None:
        assert "suggested_action_source_tutor_message_id" not in student_message.payload


@pytest.mark.parametrize(
    ("label", "persisted_kind", "event_type", "expected_candidate_count"),
    [
        ("Explain it another way", "NAVIGATION", "learning_attempt", 0),
        ("Let me try", "NAVIGATION", "learning_attempt", 0),
        ("I understand", "NAVIGATION", "learning_attempt", 0),
        ("Let's learn decimals instead", "ANSWER_CHOICE", "learning_attempt", 0),
        ("Let's learn decimals instead", "ANSWER_CHOICE", "guided_success", 0),
        ("Let's learn decimals instead", "ANSWER_CHOICE", "incorrect_attempt", 0),
        ("Let's learn decimals instead", "ANSWER_CHOICE", "misconception_signal", 0),
        ("Show me another example", "ANSWER_CHOICE", "learning_attempt", 0),
        ("B) 3", "ANSWER_CHOICE", "learning_attempt", 0),
    ],
    ids=[
        "correctly-labeled-navigation",
        "correctly-labeled-agency",
        "correctly-labeled-self-report",
        "mislabeled-topic-learning-attempt",
        "mislabeled-topic-guided-success",
        "mislabeled-topic-incorrect-attempt",
        "mislabeled-topic-misconception-signal",
        "mislabeled-support-preference",
        "unbound-answer-choice-is-generic",
    ],
)
def test_suggested_action_semantics_control_candidate_persistence(
    label: str,
    persisted_kind: str,
    event_type: str,
    expected_candidate_count: int,
) -> None:
    """ACT-02: action meaning, not a model-produced kind alone, governs click evidence."""

    session_holder: dict[str, _Session] = {}

    def metadata(_: dict[str, object]) -> dict[str, object]:
        return _candidate_for_current_message(
            session_holder["session"],
            event_type=event_type,
            signal="fixture_action_selection",
        )

    runtime, _, _, session = _runtime(_decision(), metadata)
    session_holder["session"] = session
    learning_session = SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None)
    source = LearningMessage(
        session_id=learning_session.id,
        role="tutor",
        content="Choose what you want to do next.",
        payload={"suggested_actions": [{"label": label, "kind": persisted_kind}]},
        created_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    session.add(source)

    list(runtime.stream_turn(
        learning_session=learning_session,
        question=label,
        suggested_action_kind=persisted_kind,
        suggested_action_source_tutor_message_id=source.id,
    ))

    candidates = [row for row in session.rows if isinstance(row, CandidateEvent)]
    assert len(candidates) == expected_candidate_count
    assert not candidates


def test_persisted_guided_learning_check_choice_can_create_a_bounded_attempt_candidate() -> None:
    """ACT-02: only a server-bound choice from a persisted guided check can enter the click path."""

    session_holder: dict[str, _Session] = {}

    def metadata(_: dict[str, object]) -> dict[str, object]:
        return _candidate_for_current_message(
            session_holder["session"],
            event_type="learning_attempt",
            signal="selected_division_check_choice",
        )

    runtime, _, _, session = _runtime(_decision(), metadata)
    session_holder["session"] = session
    learning_session = SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None)
    guided_check_id = uuid4()
    source = LearningMessage(
        session_id=learning_session.id,
        role="tutor",
        content="6 ÷ 2 = ?",
        payload={"guided_check": {
            "id": str(guided_check_id),
            "prompt": "6 ÷ 2 = ?",
            "choices": [{"label": "A) 2"}, {"label": "B) 3"}, {"label": "C) 4"}],
        }},
        created_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    session.add(source)

    list(runtime.stream_turn(
        learning_session=learning_session,
        question="B) 3",
        guided_check_id=guided_check_id,
        guided_check_source_tutor_message_id=source.id,
    ))

    candidate = next(row for row in session.rows if isinstance(row, CandidateEvent))
    student_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "student")
    assert candidate.event_type == "learning_attempt"
    assert student_message.payload["input_kind"] == "guided_learning_check_answer"
    assert student_message.payload["guided_check_id"] == str(guided_check_id)
    assert student_message.payload["guided_check_source_tutor_message_id"] == str(source.id)


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
    learning_session = SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None)
    guided_check_id = uuid4()
    source = LearningMessage(
        session_id=learning_session.id,
        role="tutor",
        content="Which fraction equals one half?",
        payload={"guided_check": {
            "id": str(guided_check_id),
            "prompt": "Which fraction equals one half?",
            "choices": [{"label": "1/4"}, {"label": "2/4"}, {"label": "3/4"}],
        }},
        created_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    session.add(source)
    list(runtime.stream_turn(
        learning_session=learning_session,
        question="2/4",
        guided_check_id=guided_check_id,
        guided_check_source_tutor_message_id=source.id,
    ))

    candidate = next(row for row in session.rows if isinstance(row, CandidateEvent))
    student_message = next(row for row in session.rows if isinstance(row, LearningMessage) and row.role == "student")
    assert candidate.event_type == "learning_attempt"
    assert student_message.payload["input_kind"] == "guided_learning_check_answer"


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
    learning_session = SimpleNamespace(id=uuid4(), student_id=uuid4(), subject="MATH", last_activity_at=None)
    guided_check_id = uuid4()
    source = LearningMessage(
        session_id=learning_session.id,
        role="tutor",
        content="Which fraction equals one half?",
        payload={"guided_check": {
            "id": str(guided_check_id),
            "prompt": "Which fraction equals one half?",
            "choices": [{"label": "1/4"}, {"label": "2/4"}, {"label": "3/4"}],
        }},
        created_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    session.add(source)
    list(runtime.stream_turn(
        learning_session=learning_session,
        question="2/4",
        guided_check_id=guided_check_id,
        guided_check_source_tutor_message_id=source.id,
    ))

    tutor_message = [row for row in session.rows if isinstance(row, LearningMessage) and row.role == "tutor"][-1]
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
