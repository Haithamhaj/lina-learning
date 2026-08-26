"""PostgreSQL contracts for CTX-03B same-call Segment relation and state."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import os
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import LearningMessage, LearningSegment, LearningSession, ModelTask, Student, User
from services.platform.safety import SafetyAction, SafetyDecision
from services.retrieval.service import RetrievedBlock
from services.tutor.context import SessionContextMessage, TutorContext, TutorContextDebug
from services.tutor.runtime import TutorModelStreamFailure, TutorRuntime, TutorTurn
from services.tutor.segments import SEGMENT_STATE_SCHEMA_VERSION


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Segment runtime tests",
)


_MISSING = object()


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE candidate_events, learning_messages, learning_segments, ai_executions, "
                "learning_sessions, students, users CASCADE"
            )
        )
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _learning_session(session: Session) -> LearningSession:
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="fixture")
    session.add(student)
    session.flush()
    learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
    session.add(learning_session)
    session.flush()
    return learning_session


class _ContextBuilder:
    """A controlled context boundary; Segment runtime must not rewrite CTX-02 selections."""

    def __init__(self, *, immediate_exchange: tuple[SessionContextMessage, ...] = ()) -> None:
        self.immediate_exchange = immediate_exchange
        self.calls = 0

    def build(
        self,
        *,
        learning_session: LearningSession,
        question: str,
        current_turn_message_id: UUID | None = None,
    ) -> TutorContext:
        self.calls += 1
        current_id = current_turn_message_id or uuid4()
        block = RetrievedBlock(
            text="Equivalent fractions name the same amount.",
            source_ref="book#page=12",
            page_number=12,
            block_type="EXERCISE",
            score=1.0,
            semantic_key="fractions",
            semantic_type="EXERCISE",
            concept_key="fractions",
            source_refs=("book#page=12",),
            page_numbers=(12,),
            matched=True,
        )
        return TutorContext(
            question=question,
            subject=learning_session.subject,
            grade_level=5,
            focus=None,
            immediate_exchange=self.immediate_exchange,
            session_messages=(SessionContextMessage(current_id, "student", question),),
            retrieval=(block,),
            intelligence=(),
            debug=TutorContextDebug(
                None,
                (current_id,),
                ("book#page=12",),
                (),
                (),
                current_turn_message_id=current_id,
                immediate_exchange_message_ids=tuple(message.message_id for message in self.immediate_exchange),
                older_continuity_message_ids=(current_id,),
            ),
        )


class _Policy:
    def evaluate(self, **_: object) -> SafetyDecision:
        return SafetyDecision(SafetyAction.ALLOW, None, "BASELINE", 1, "TEST_ALLOW", "normal", None)


class _ScriptedProvider:
    def __init__(self, outputs: list[dict[str, object] | Callable[[dict[str, object]], dict[str, object]]]) -> None:
        self.outputs = iter(outputs)
        self.calls: list[dict[str, object]] = []

    def stream(self, route: ModelRoute, payload: dict[str, object]) -> Iterator[StreamDelta | StreamComplete]:
        del route
        self.calls.append(payload)
        output = next(self.outputs)
        resolved = output(payload) if callable(output) else output
        yield StreamDelta(str(resolved["text"]))
        yield StreamComplete(ModelResult(output=resolved, input_tokens=4, output_tokens=3))


class _FailingProvider:
    def stream(self, route: ModelRoute, payload: dict[str, object]) -> Iterator[StreamDelta | StreamComplete]:
        del route, payload
        raise RuntimeError("fixture stream failure")
        yield  # pragma: no cover


def _output(
    *,
    text: str = "Try one small step.",
    relation: object = _MISSING,
    state: object = _MISSING,
    suggested_actions: object = _MISSING,
) -> dict[str, object]:
    output: dict[str, object] = {
        "text": text,
        "suggested_actions": [] if suggested_actions is _MISSING else suggested_actions,
        "teaching_mode": None,
        "teaching_strategy": None,
        "teaching_method_id": None,
        "prior_method_relation": None,
        "candidate_metadata": None,
    }
    if relation is not _MISSING:
        output["segment_relation"] = relation
    if state is not _MISSING:
        output["structured_segment_state"] = state
    return output


def _state(payload: dict[str, object], *, goal: str = "Compare equivalent fractions", **extra: object) -> dict[str, object]:
    return {
        "schema_version": SEGMENT_STATE_SCHEMA_VERSION,
        "active_goal": goal,
        "unresolved_point": "The Student's current question remains open.",
        "active_references": [],
        "established_facts": [],
        "source_message_ids": [payload["candidate_source_message_id"]],
        **extra,
    }


def _runtime(
    session: Session,
    provider: object,
    *,
    context_builder: _ContextBuilder | None = None,
) -> tuple[TutorRuntime, _ContextBuilder]:
    context = context_builder or _ContextBuilder()
    gateway = ModelGateway(
        session,
        routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")},
        providers={"fixture": provider},
    )
    return TutorRuntime(session, context_builder=context, safety_policy=_Policy(), gateway=gateway), context


def _messages(session: Session, learning_session: LearningSession) -> list[LearningMessage]:
    return list(
        session.scalars(
            select(LearningMessage)
            .where(LearningMessage.session_id == learning_session.id)
            .order_by(LearningMessage.created_at, LearningMessage.id)
        )
    )


def test_first_successful_exchange_creates_segment_one_and_normalizes_relation(factory: sessionmaker[Session]) -> None:
    """Catches a first turn inventing a prior Segment or leaving its pair unassigned."""

    with factory.begin() as session:
        learning_session = _learning_session(session)
        provider = _ScriptedProvider([lambda payload: _output(relation="CONTINUE", state=_state(payload))])
        runtime, _ = _runtime(session, provider)

        turn = list(runtime.stream_turn(learning_session=learning_session, question="Explain one half."))[-1]
        segment = session.scalar(select(LearningSegment).where(LearningSegment.session_id == learning_session.id))
        student, tutor = _messages(session, learning_session)

        assert isinstance(turn, TutorTurn)
        assert segment is not None
        assert segment.sequence == 1
        assert student.segment_id == tutor.segment_id == segment.id
        assert student.payload["conversation"]["segment_relation"] is None
        assert student.payload["conversation"]["relation_source"] == "STRUCTURAL_FIRST_SEGMENT"
        assert segment.structured_state["source_message_ids"] == [str(student.id)]
        assert len(provider.calls) == 1


def test_continue_updates_one_segment_projection_without_erasing_raw_messages(factory: sessionmaker[Session]) -> None:
    """Catches CONTINUE creating a new Segment or replacing raw-source authority."""

    with factory.begin() as session:
        learning_session = _learning_session(session)
        provider = _ScriptedProvider([
            lambda payload: _output(relation="NEW_SEGMENT", state=_state(payload, goal="Start fractions")),
            lambda payload: _output(relation="CONTINUE", state=_state(payload, goal="Compare equivalent fractions")),
        ])
        runtime, _ = _runtime(session, provider)

        list(runtime.stream_turn(learning_session=learning_session, question="What is one half?"))
        first_student, first_tutor = _messages(session, learning_session)
        list(runtime.stream_turn(learning_session=learning_session, question="Why is two fourths the same?"))
        messages = _messages(session, learning_session)
        segment = session.scalar(select(LearningSegment).where(LearningSegment.session_id == learning_session.id))

        assert segment is not None
        assert segment.sequence == 1
        assert [message.segment_id for message in messages] == [segment.id] * 4
        assert segment.structured_state["active_goal"] == "Compare equivalent fractions"
        assert first_student.content == "What is one half?"
        assert first_tutor.content == "Try one small step."
        assert messages[2].payload["conversation"]["segment_relation"] == "CONTINUE"
        assert messages[2].payload["conversation"]["relation_source"] == "LUNA"


@pytest.mark.parametrize("relation", ["NEW_SEGMENT", "UNCERTAIN"])
def test_new_or_uncertain_relation_creates_an_independent_next_segment(
    factory: sessionmaker[Session], relation: str
) -> None:
    """Catches a topic transition or uncertainty contaminating the prior Segment."""

    with factory.begin() as session:
        learning_session = _learning_session(session)
        provider = _ScriptedProvider([
            lambda payload: _output(relation="NEW_SEGMENT", state=_state(payload, goal="Fractions")),
            lambda payload: _output(relation=relation, state=_state(payload, goal="Different orientation")),
        ])
        runtime, _ = _runtime(session, provider)

        list(runtime.stream_turn(learning_session=learning_session, question="Help with fractions."))
        first_segment = session.scalar(select(LearningSegment).where(LearningSegment.session_id == learning_session.id))
        list(runtime.stream_turn(learning_session=learning_session, question="Can we talk about something else?"))
        segments = list(session.scalars(select(LearningSegment).where(LearningSegment.session_id == learning_session.id).order_by(LearningSegment.sequence)))
        messages = _messages(session, learning_session)

        assert first_segment is not None
        assert [segment.sequence for segment in segments] == [1, 2]
        assert messages[0].segment_id == messages[1].segment_id == segments[0].id
        assert messages[2].segment_id == messages[3].segment_id == segments[1].id
        assert messages[2].payload["conversation"]["segment_relation"] == relation
        assert messages[2].payload["conversation"]["relation_source"] == "LUNA"
        assert segments[1].structured_state["active_goal"] == "Different orientation"


@pytest.mark.parametrize("relation", [_MISSING, "NOT_A_RELATION", None])
def test_missing_or_invalid_relation_uses_conservative_new_ephemeral_fallback(
    factory: sessionmaker[Session], relation: object
) -> None:
    """Catches malformed Luna metadata silently joining the active Segment."""

    with factory.begin() as session:
        learning_session = _learning_session(session)
        provider = _ScriptedProvider([
            lambda payload: _output(relation="NEW_SEGMENT", state=_state(payload)),
            lambda payload: _output(relation=relation, state=_state(payload, goal="Fallback orientation")),
        ])
        runtime, _ = _runtime(session, provider)

        list(runtime.stream_turn(learning_session=learning_session, question="First topic."))
        list(runtime.stream_turn(learning_session=learning_session, question="Ambiguous next topic."))
        segments = list(session.scalars(select(LearningSegment).where(LearningSegment.session_id == learning_session.id).order_by(LearningSegment.sequence)))
        student = _messages(session, learning_session)[2]

        assert [segment.sequence for segment in segments] == [1, 2]
        assert student.segment_id == segments[1].id
        assert student.payload["conversation"]["segment_relation"] == "UNCERTAIN"
        assert student.payload["conversation"]["relation_source"] == "FALLBACK"


def test_state_rejects_cross_segment_source_and_new_segment_never_inherits_state(factory: sessionmaker[Session]) -> None:
    """Catches a latest-state projection accepting foreign raw lineage or copying prior state."""

    with factory.begin() as session:
        learning_session = _learning_session(session)

        def foreign_state(_: dict[str, object]) -> dict[str, object]:
            first_student = _messages(session, learning_session)[0]
            return _output(relation="NEW_SEGMENT", state={
                "schema_version": SEGMENT_STATE_SCHEMA_VERSION,
                "active_goal": "Foreign source must be rejected",
                "unresolved_point": None,
                "active_references": [],
                "established_facts": [],
                "source_message_ids": [str(first_student.id)],
            })

        provider = _ScriptedProvider([
            lambda payload: _output(relation="NEW_SEGMENT", state=_state(payload, goal="Prior state")),
            foreign_state,
        ])
        runtime, _ = _runtime(session, provider)

        list(runtime.stream_turn(learning_session=learning_session, question="First topic."))
        list(runtime.stream_turn(learning_session=learning_session, question="New topic."))
        segments = list(session.scalars(select(LearningSegment).where(LearningSegment.session_id == learning_session.id).order_by(LearningSegment.sequence)))

        assert segments[0].structured_state["active_goal"] == "Prior state"
        assert segments[1].structured_state is None


def test_state_rejects_extra_learner_profile_fields_without_losing_valid_tutor_text(factory: sessionmaker[Session]) -> None:
    """Catches learner-intelligence leakage or malformed state breaking a valid Tutor response."""

    with factory.begin() as session:
        learning_session = _learning_session(session)

        def leaked_state(payload: dict[str, object]) -> dict[str, object]:
            return _output(
                relation="NEW_SEGMENT",
                state=_state(payload, mastery="high", learner_strengths=["fractions"]),
                suggested_actions=[{"label": "Let me try", "kind": "NAVIGATION"}],
            )

        provider = _ScriptedProvider([leaked_state])
        runtime, _ = _runtime(session, provider)

        turn = list(runtime.stream_turn(learning_session=learning_session, question="I am stuck."))[-1]
        segment = session.scalar(select(LearningSegment).where(LearningSegment.session_id == learning_session.id))
        student, tutor = _messages(session, learning_session)

        assert isinstance(turn, TutorTurn)
        assert segment is not None and segment.structured_state is None
        assert tutor.payload["suggested_actions"] == [{"label": "Let me try", "kind": "NAVIGATION"}]
        assert student.payload["conversation"]["state_status"] == "invalid"


def test_latest_valid_state_enters_same_primary_call_with_exact_immediate_lineage(factory: sessionmaker[Session]) -> None:
    """Catches CTX-02 bridge content being preserved while its exact raw lineage is dropped."""

    with factory.begin() as session:
        learning_session = _learning_session(session)
        provider = _ScriptedProvider([
            lambda payload: _output(relation="NEW_SEGMENT", state=_state(payload, goal="Fractions")),
            lambda payload: _output(relation="CONTINUE", state=_state(payload, goal="Equivalent fractions")),
        ])
        runtime, _ = _runtime(session, provider)
        list(runtime.stream_turn(learning_session=learning_session, question="Start fractions."))
        first_student, first_tutor = _messages(session, learning_session)
        context = _ContextBuilder(
            immediate_exchange=(
                SessionContextMessage(first_student.id, "student", first_student.content),
                SessionContextMessage(first_tutor.id, "tutor", first_tutor.content),
            )
        )
        runtime, _ = _runtime(session, provider, context_builder=context)

        list(runtime.stream_turn(learning_session=learning_session, question="Continue fractions."))
        payload = provider.calls[-1]

        assert f"student message [{first_student.id}]:\nStart fractions." in str(payload["input"])
        assert f"tutor message [{first_tutor.id}]:\nTry one small step." in str(payload["input"])
        assert "Latest confirmed Segment State" in str(payload["input"])
        assert "Fractions" in str(payload["input"])
        assert len(provider.calls) == 2


def test_state_can_cite_exact_prior_tutor_and_repeated_student_ids(factory: sessionmaker[Session]) -> None:
    """Catches state lineage that cannot distinguish two identical raw messages by their persisted IDs."""

    with factory.begin() as session:
        learning_session = _learning_session(session)
        provider = _ScriptedProvider([
            lambda _: _output(text="One half is the same as two fourths.", relation="NEW_SEGMENT", state=None),
            lambda payload: _output(
                relation="CONTINUE",
                state={
                    "schema_version": SEGMENT_STATE_SCHEMA_VERSION,
                    "active_goal": "Continue equivalent fractions",
                    "unresolved_point": None,
                    "active_references": [],
                    "established_facts": ["One half is the same as two fourths."],
                    "source_message_ids": [
                        str(first_student.id),
                        str(first_tutor.id),
                        payload["candidate_source_message_id"],
                    ],
                },
            ),
        ])
        runtime, _ = _runtime(session, provider)
        list(runtime.stream_turn(learning_session=learning_session, question="same words"))
        first_student, first_tutor = _messages(session, learning_session)
        context = _ContextBuilder(
            immediate_exchange=(
                SessionContextMessage(first_student.id, "student", first_student.content),
                SessionContextMessage(first_tutor.id, "tutor", first_tutor.content),
            )
        )
        runtime, _ = _runtime(session, provider, context_builder=context)

        list(runtime.stream_turn(learning_session=learning_session, question="same words"))
        current_student = _messages(session, learning_session)[2]
        segment = session.scalar(select(LearningSegment).where(LearningSegment.session_id == learning_session.id))
        payload = provider.calls[-1]

        assert segment is not None
        assert first_student.id != current_student.id
        assert f"student message [{first_student.id}]:\nsame words" in str(payload["input"])
        assert f"tutor message [{first_tutor.id}]:\nOne half is the same as two fourths." in str(payload["input"])
        assert f"Current Student raw source ID: [{current_student.id}]" in str(payload["input"])
        assert segment.structured_state["source_message_ids"] == [
            str(first_student.id),
            str(first_tutor.id),
            str(current_student.id),
        ]


def test_state_rejects_an_invented_source_id_without_losing_tutor_text(factory: sessionmaker[Session]) -> None:
    """Catches a fabricated raw identifier being accepted as Segment State provenance."""

    with factory.begin() as session:
        learning_session = _learning_session(session)

        def invented_source(payload: dict[str, object]) -> dict[str, object]:
            return _output(
                relation="NEW_SEGMENT",
                state={
                    "schema_version": SEGMENT_STATE_SCHEMA_VERSION,
                    "active_goal": "Must not persist",
                    "unresolved_point": None,
                    "active_references": [],
                    "established_facts": [],
                    "source_message_ids": [str(uuid4())],
                },
            )

        runtime, _ = _runtime(session, _ScriptedProvider([invented_source]))
        turn = list(runtime.stream_turn(learning_session=learning_session, question="A valid answer remains."))[-1]
        segment = session.scalar(select(LearningSegment).where(LearningSegment.session_id == learning_session.id))
        student, _ = _messages(session, learning_session)

        assert isinstance(turn, TutorTurn)
        assert segment is not None and segment.structured_state is None
        assert student.payload["conversation"]["state_status"] == "invalid"


def test_state_rejects_same_segment_source_not_exposed_to_this_call(factory: sessionmaker[Session]) -> None:
    """Catches State provenance citing arbitrary older Segment history rather than visible raw lineage."""

    with factory.begin() as session:
        learning_session = _learning_session(session)
        provider = _ScriptedProvider([
            lambda payload: _output(relation="NEW_SEGMENT", state=_state(payload, goal="First orientation")),
            lambda payload: _output(relation="CONTINUE", state=_state(payload, goal="Second orientation")),
            lambda _: _output(
                relation="CONTINUE",
                state={
                    "schema_version": SEGMENT_STATE_SCHEMA_VERSION,
                    "active_goal": "Must not use hidden old history",
                    "unresolved_point": None,
                    "active_references": [],
                    "established_facts": [],
                    "source_message_ids": [str(first_tutor.id)],
                },
            ),
        ])
        runtime, _ = _runtime(session, provider)
        list(runtime.stream_turn(learning_session=learning_session, question="first question"))
        first_student, first_tutor = _messages(session, learning_session)
        runtime, _ = _runtime(
            session,
            provider,
            context_builder=_ContextBuilder(
                immediate_exchange=(
                    SessionContextMessage(first_student.id, "student", first_student.content),
                    SessionContextMessage(first_tutor.id, "tutor", first_tutor.content),
                )
            ),
        )
        list(runtime.stream_turn(learning_session=learning_session, question="second question"))
        second_student, second_tutor = _messages(session, learning_session)[2:]
        runtime, _ = _runtime(
            session,
            provider,
            context_builder=_ContextBuilder(
                immediate_exchange=(
                    SessionContextMessage(second_student.id, "student", second_student.content),
                    SessionContextMessage(second_tutor.id, "tutor", second_tutor.content),
                )
            ),
        )

        list(runtime.stream_turn(learning_session=learning_session, question="third question"))
        segment = session.scalar(select(LearningSegment).where(LearningSegment.session_id == learning_session.id))
        current_student = _messages(session, learning_session)[4]

        assert segment is not None
        assert current_student.payload["conversation"]["state_status"] == "invalid"
        assert segment.structured_state["active_goal"] == "Second orientation"


def test_failed_stream_keeps_raw_student_unsegmented_and_creates_no_tutor_exchange(factory: sessionmaker[Session]) -> None:
    """Catches failure-path fabrication of a completed Exchange or semantic relation."""

    with factory.begin() as session:
        learning_session = _learning_session(session)
        runtime, _ = _runtime(session, _FailingProvider())

        with pytest.raises(TutorModelStreamFailure):
            list(runtime.stream_turn(learning_session=learning_session, question="A raw question survives failure."))

        messages = _messages(session, learning_session)
        assert len(messages) == 1
        assert messages[0].role == "student"
        assert messages[0].segment_id is None
        assert "conversation" not in messages[0].payload
        assert session.scalar(select(LearningSegment).where(LearningSegment.session_id == learning_session.id)) is None
