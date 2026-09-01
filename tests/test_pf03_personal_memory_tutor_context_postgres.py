"""PF-03 contracts for full current Personal Memory in the existing Tutor call."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

import services.tutor.context as tutor_context_module
from services.personal_facts.memory_document import format_current_personal_memory_card
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import LearningSession, PersonalFact, Student, User
from services.tutor.capacity import apply_context_capacity_guardrail, serialized_model_request_characters
from services.tutor.context import TutorContext, TutorContextBuilder, TutorContextDebug
from services.tutor.runtime import TUTOR_SHARED_INSTRUCTIONS, build_tutor_model_payload


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for PF-03 tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


class _NoopRetrieval:
    def retrieve(self, **_: object) -> list[object]:
        return []


def _student_and_session(session: Session, suffix: str) -> tuple[Student, LearningSession]:
    user = User(identity_provider="fixture", external_subject=f"pf03-{suffix}-{uuid4().hex}", role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name=f"Student {suffix}")
    session.add(student)
    session.flush()
    learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN")
    session.add(learning_session)
    session.flush()
    return student, learning_session


def _fact(
    session: Session,
    *,
    student: Student,
    category: str,
    fact_key: str,
    value: str,
    display_statement: str,
    observed_at: datetime,
) -> PersonalFact:
    fact = PersonalFact(
        student_id=student.id,
        category=category,
        fact_key=fact_key,
        value=value,
        display_statement=display_statement,
        support_count=1,
        first_observed_at=observed_at,
        last_observed_at=observed_at,
    )
    session.add(fact)
    session.flush()
    return fact


def test_full_current_memory_card_includes_every_current_fact_without_metadata(
    factory: sessionmaker[Session],
) -> None:
    """Catches relevance filtering, history leakage, or metadata exposure in PF-03."""

    base = datetime(2026, 9, 1, 10, tzinfo=UTC)
    with factory.begin() as session:
        student, _ = _student_and_session(session, "full-card")
        _fact(session, student=student, category="PREFERENCE", fact_key="preference:drawing", value="LIKE", display_statement="Likes drawing", observed_at=base)
        _fact(session, student=student, category="PREFERENCE", fact_key="preference:drawing", value="DISLIKE", display_statement="Does not currently like drawing", observed_at=base + timedelta(minutes=1))
        _fact(session, student=student, category="PREFERENCE", fact_key="preference:photography", value="LIKE", display_statement="Likes photography", observed_at=base)
        _fact(session, student=student, category="FAVORITE", fact_key="favorite:color", value="PURPLE", display_statement="Favorite color is purple", observed_at=base)
        _fact(session, student=student, category="ACTIVITY", fact_key="activity:basketball", value="PLAYS", display_statement="Plays basketball every Thursday", observed_at=base)
        _fact(session, student=student, category="PET", fact_key="pet:cat", value="LUNA", display_statement="Has a cat named Luna", observed_at=base)

        card = format_current_personal_memory_card(session, student_id=student.id)

    assert card == (
        "Preferences:\n- Does not currently like drawing\n- Likes photography\n\n"
        "Favorites:\n- Favorite color is purple\n\n"
        "Activities:\n- Plays basketball every Thursday\n\n"
        "Pets:\n- Has a cat named Luna"
    )
    for forbidden in ("Likes drawing", "support_count", "last_observed_at", "historical_fact_count", "fact_id"):
        assert forbidden not in card


def test_historical_return_restores_only_the_newest_like_to_tutor_memory(
    factory: sessionmaker[Session],
) -> None:
    """Catches a current-value projection that cannot return to an older Fact identity."""

    base = datetime(2026, 9, 1, 10, tzinfo=UTC)
    with factory.begin() as session:
        student, _ = _student_and_session(session, "historical-return")
        like = _fact(session, student=student, category="PREFERENCE", fact_key="preference:drawing", value="LIKE", display_statement="Likes drawing", observed_at=base)
        _fact(session, student=student, category="PREFERENCE", fact_key="preference:drawing", value="DISLIKE", display_statement="Does not like drawing", observed_at=base + timedelta(minutes=1))
        like.last_observed_at = base + timedelta(minutes=2)

        card = format_current_personal_memory_card(session, student_id=student.id)

    assert card == "Preferences:\n- Likes drawing"


def test_tutor_context_keeps_full_memory_for_irrelevant_math_and_cross_student_isolation(
    factory: sessionmaker[Session],
) -> None:
    """Catches question-based selection or a Personal Fact query not scoped to the Session Student."""

    now = datetime(2026, 9, 1, 10, tzinfo=UTC)
    with factory.begin() as session:
        student_a, session_a = _student_and_session(session, "a")
        student_b, session_b = _student_and_session(session, "b")
        for index in range(25):
            _fact(session, student=student_a, category="ACTIVITY", fact_key=f"activity:hobby_{index}", value="LIKES", display_statement=f"Likes hobby {index}", observed_at=now)
        _fact(session, student=student_b, category="PET", fact_key="pet:dog", value="MAX", display_statement="Has a dog named Max", observed_at=now)

        builder = TutorContextBuilder(session, retrieval_service=_NoopRetrieval())
        context_a = builder.build(learning_session=session_a, question="What is 7 × 8?")
        context_b = builder.build(learning_session=session_b, question="ممكن تشرحلي بطريقة ممتعة؟")

    assert context_a.personal_memory is not None
    assert all(f"Likes hobby {index}" in context_a.personal_memory for index in range(25))
    assert "Has a dog named Max" not in context_a.personal_memory
    assert context_b.personal_memory == "Pets:\n- Has a dog named Max"
    payload = build_tutor_model_payload(question=context_a.question, personal_memory=context_a.personal_memory)
    assert context_a.personal_memory in str(payload["input"])
    assert str(payload["input"]).index("Personal Memory") < str(payload["input"]).index("Current Turn")


def test_current_student_statement_and_personal_memory_remain_separate_with_current_turn_authority() -> None:
    """Catches a prompt that lets stale Personal Memory outrank the current Student conversation."""

    payload = build_tutor_model_payload(
        question="I don't like drawing anymore.",
        personal_memory="Preferences:\n- Likes drawing",
        student_core_context={"display_name": "Lina", "age_years": 10, "grade_level": 5},
    )

    assert "I don't like drawing anymore." in str(payload["input"])
    assert "Preferences:\n- Likes drawing" in str(payload["input"])
    assert payload["personal_memory"] == "Preferences:\n- Likes drawing"
    instructions = TUTOR_SHARED_INSTRUCTIONS.casefold()
    assert "personal memory contains prior explicit student-provided personal context" in instructions
    assert "current student conversation wins immediately" in instructions
    assert "do not infer extra traits" in instructions


def test_capacity_omits_the_entire_personal_memory_block_without_partial_selection() -> None:
    """Catches capacity handling that trims arbitrary facts instead of omitting PF-03 as one unit."""

    context = TutorContext(
        question="What is 7 × 8?",
        subject="MATH",
        grade_level=5,
        focus=None,
        session_messages=(),
        retrieval=(),
        intelligence=(),
        debug=TutorContextDebug(None, (), (), (), ()),
        personal_memory="Activities:\n" + "\n".join(f"- Likes hobby {index}" for index in range(30)),
    )
    payload_builder = lambda selected: build_tutor_model_payload(
        question=selected.question,
        personal_memory=selected.personal_memory,
    )
    without_memory = payload_builder(TutorContext(
        question=context.question, subject=context.subject, grade_level=context.grade_level,
        focus=None, session_messages=(), retrieval=(), intelligence=(), debug=context.debug,
    ))

    result = apply_context_capacity_guardrail(
        context,
        capacity_limit=serialized_model_request_characters(without_memory),
        payload_builder=payload_builder,
    )

    assert result.context.personal_memory is None
    assert result.context.debug.personal_memory_status == "PERSONAL_MEMORY_OMITTED_CAPACITY"
    assert result.lineage.dropped_context[0].kind == "PERSONAL_MEMORY"
    assert result.lineage.dropped_context[0].reason == "PERSONAL_MEMORY_OMITTED_CAPACITY"
    assert "Likes hobby 0" not in str(result.payload["input"])
    assert "Likes hobby 29" not in str(result.payload["input"])


def test_operational_personal_memory_read_failure_omits_only_memory(
    factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches a PF read outage that wrongly blocks the existing Tutor context build."""

    with factory.begin() as session:
        _, learning_session = _student_and_session(session, "read-failure")

        def fail_read(*_: object, **__: object) -> str | None:
            raise OperationalError("SELECT", {}, RuntimeError("fixture database read failure"))

        monkeypatch.setattr(tutor_context_module, "format_current_personal_memory_card", fail_read)
        context = TutorContextBuilder(session, retrieval_service=_NoopRetrieval()).build(
            learning_session=learning_session,
            question="What is 7 × 8?",
        )

    assert context.personal_memory is None
    assert context.debug.personal_memory_status == "PERSONAL_MEMORY_OMITTED_ERROR"


def test_student_without_personal_facts_uses_the_existing_tutor_context_without_a_memory_block(
    factory: sessionmaker[Session],
) -> None:
    """Catches fake/default personalization when the Student has no Personal Facts."""

    with factory.begin() as session:
        _, learning_session = _student_and_session(session, "no-facts")
        context = TutorContextBuilder(session, retrieval_service=_NoopRetrieval()).build(
            learning_session=learning_session,
            question="What is 7 × 8?",
        )

    payload = build_tutor_model_payload(question=context.question, personal_memory=context.personal_memory)
    assert context.personal_memory is None
    assert context.debug.personal_memory_status == "PERSONAL_MEMORY_NOT_AVAILABLE"
    assert "Personal Memory — prior Student-provided context" not in str(payload["input"])
