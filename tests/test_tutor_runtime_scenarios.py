"""Compact deterministic golden scenarios for the production Tutor orchestration."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.platform.db.models import LearningMessage, ModelTask
from services.platform.safety import SafetyAction, SafetyDecision
from services.retrieval.service import RetrievedBlock
from services.tutor.context import SessionContextMessage, TutorContext, TutorContextDebug
from services.tutor.runtime import TeachingMode, TeachingStrategy, TutorRuntime, TutorTextDelta, TutorTurn


class _Session:
    def __init__(self) -> None:
        self.rows: list[object] = []

    def add(self, row: object) -> None:
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
    def __init__(self, text: str = "Try one small step.") -> None:
        self.calls = 0
        self.payloads: list[dict[str, object]] = []
        self.text = text

    def stream(self, route: ModelRoute, payload: dict[str, object]):
        del route
        self.calls += 1
        self.payloads.append(payload)
        yield StreamDelta(self.text[:8])
        yield StreamDelta(self.text[8:])
        yield StreamComplete(ModelResult(output={"text": self.text}, input_tokens=4, output_tokens=3))


def _decision(action: SafetyAction = SafetyAction.ALLOW, directive: str | None = None) -> SafetyDecision:
    return SafetyDecision(action, None, "BASELINE", 1, f"TEST_{action.value}", "normal", directive)


def _runtime(decision: SafetyDecision) -> tuple[TutorRuntime, _ContextBuilder, _Provider, _Session]:
    session = _Session()
    context = _ContextBuilder()
    provider = _Provider()
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


@pytest.mark.parametrize("action", [SafetyAction.REDIRECT_TO_PARENT, SafetyAction.BLOCK])
def test_redirect_and_protected_actions_persist_policy_response_without_a_model_call(action: SafetyAction) -> None:
    runtime, context, provider, session = _runtime(_decision(action, "Please talk with a trusted grown-up."))

    events = list(runtime.stream_turn(learning_session=SimpleNamespace(id=uuid4(), student_id=uuid4(), last_activity_at=None), question="Can you help?"))

    assert isinstance(events[-1], TutorTurn)
    assert events[-1].text == "Please talk with a trusted grown-up."
    assert context.calls == 0
    assert provider.calls == 0
    assert len([row for row in session.rows if isinstance(row, LearningMessage)]) == 2


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
