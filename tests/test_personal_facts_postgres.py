"""PostgreSQL contracts for the independent Personal Facts domain."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.personal_facts.extraction import (
    PersonalFactCandidate,
    PersonalFactsExtractionEnvelope,
    SupportingAssertion,
    extraction_request,
    validate_extraction_output,
)
from services.personal_facts.memory_document import build_personal_memory_document
from services.personal_facts.reconciliation import reconcile_candidates
from services.platform.db.connection import normalize_database_url
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StaticModelProvider
from services.platform.config import Settings
from services.platform.db.models import Job, LearningMessage, LearningSession, ModelTask, PersonalFact, PersonalFactExtractionRun, PersonalFactObservation, Student, User
from services.tutor.session_lifecycle import SessionLifecyclePolicy, close_session_if_eligible
from workers.job_worker import JobHandlerRegistry, run_once
from workers.personal_facts_handlers import PERSONAL_FACTS_EXTRACTION_JOB, register_personal_facts_handlers


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Personal Facts tests",
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE jobs, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _student(session: Session, *, suffix: str) -> Student:
    user = User(identity_provider="fixture", external_subject=f"pf-{suffix}-{uuid4().hex}", role="STUDENT")
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name=f"Student {suffix}")
    session.add(student)
    session.flush()
    return student


def _closed_session(session: Session, *, student: Student) -> LearningSession:
    closed_at = datetime(2026, 9, 1, 12, tzinfo=UTC)
    learning_session = LearningSession(
        student_id=student.id,
        subject="MATH",
        status="CLOSED",
        last_activity_at=closed_at,
        closed_at=closed_at,
    )
    session.add(learning_session)
    session.flush()
    return learning_session


def _message(
    session: Session,
    *,
    learning_session: LearningSession,
    role: str,
    content: str,
    created_at: datetime,
) -> LearningMessage:
    message = LearningMessage(
        session_id=learning_session.id,
        role=role,
        content=content,
        created_at=created_at,
    )
    session.add(message)
    session.flush()
    return message


def _candidate(message: LearningMessage, *, value: str = "LIKE") -> PersonalFactCandidate:
    assertion = "I like drawing" if value == "LIKE" else "I don't like drawing anymore"
    return PersonalFactCandidate(
        category="PREFERENCE",
        fact_key="preference:drawing",
        value=value,
        display_statement="Likes drawing" if value == "LIKE" else "Does not like drawing",
        supporting_assertions=[
            SupportingAssertion(
                source_message_id=message.id,
                explicit_student_assertion=assertion,
            )
        ],
    )


def test_reconciliation_adds_support_preserves_history_and_projects_latest_value(
    factory: sessionmaker[Session],
) -> None:
    """Catches overwriting contrary values or deriving counts from retries instead of sources."""

    with factory.begin() as session:
        student = _student(session, suffix="a")
        learning_session = _closed_session(session, student=student)
        first = _message(
            session,
            learning_session=learning_session,
            role="student",
            content="I like drawing.",
            created_at=datetime(2026, 7, 1, 10, tzinfo=UTC),
        )
        second = _message(
            session,
            learning_session=learning_session,
            role="student",
            content="I like drawing.",
            created_at=datetime(2026, 8, 1, 10, tzinfo=UTC),
        )
        contrary = _message(
            session,
            learning_session=learning_session,
            role="student",
            content="I don't like drawing anymore.",
            created_at=datetime(2026, 9, 1, 10, tzinfo=UTC),
        )

        first_result = reconcile_candidates(
            session, student_id=student.id, learning_session=learning_session, candidates=[_candidate(first)]
        )
        support_result = reconcile_candidates(
            session, student_id=student.id, learning_session=learning_session, candidates=[_candidate(second)]
        )
        repeat_result = reconcile_candidates(
            session, student_id=student.id, learning_session=learning_session, candidates=[_candidate(second)]
        )
        contrary_result = reconcile_candidates(
            session, student_id=student.id, learning_session=learning_session, candidates=[_candidate(contrary, value="DISLIKE")]
        )
        projection = build_personal_memory_document(session, student_id=student.id)

        assert first_result == {"added": 1, "supported": 0, "noop": 0}
        assert support_result == {"added": 0, "supported": 1, "noop": 0}
        assert repeat_result == {"added": 0, "supported": 0, "noop": 1}
        assert contrary_result == {"added": 1, "supported": 0, "noop": 0}
        assert projection["Preferences"] == [
            {
                "fact_key": "preference:drawing",
                "value": "DISLIKE",
                "display_statement": "Does not like drawing",
                "support_count": 1,
                "last_observed_at": "2026-09-01T10:00:00+00:00",
            }
        ]
        assert projection["historical_fact_count"] == 2


def test_validation_rejects_tutor_cross_student_and_ungrounded_sources(
    factory: sessionmaker[Session],
) -> None:
    """Catches model output creating a Fact from non-Student or foreign raw history."""

    with factory.begin() as session:
        student_a = _student(session, suffix="a")
        student_b = _student(session, suffix="b")
        session_a = _closed_session(session, student=student_a)
        session_b = _closed_session(session, student=student_b)
        tutor = _message(
            session,
            learning_session=session_a,
            role="tutor",
            content="You like drawing.",
            created_at=datetime(2026, 9, 1, 9, tzinfo=UTC),
        )
        foreign = _message(
            session,
            learning_session=session_b,
            role="student",
            content="I like drawing.",
            created_at=datetime(2026, 9, 1, 9, tzinfo=UTC),
        )

        tutor_envelope = PersonalFactsExtractionEnvelope(
            version="personal-facts-extraction-v1",
            candidates=[_candidate(tutor)],
        )
        foreign_envelope = PersonalFactsExtractionEnvelope(
            version="personal-facts-extraction-v1",
            candidates=[_candidate(foreign)],
        )

        assert validate_extraction_output(session, student_id=student_a.id, learning_session=session_a, envelope=tutor_envelope) == []
        assert validate_extraction_output(session, student_id=student_a.id, learning_session=session_a, envelope=foreign_envelope) == []


def test_validation_rejects_sensitive_and_core_profile_competing_candidates(
    factory: sessionmaker[Session],
) -> None:
    """Catches a candidate guard weakening into model-only sensitive-data acceptance."""

    with factory.begin() as session:
        student = _student(session, suffix="a")
        learning_session = _closed_session(session, student=student)
        message = _message(
            session,
            learning_session=learning_session,
            role="student",
            content="My password is secret123 and I am 14.",
            created_at=datetime(2026, 9, 1, 9, tzinfo=UTC),
        )
        envelope = PersonalFactsExtractionEnvelope(
            version="personal-facts-extraction-v1",
            candidates=[
                PersonalFactCandidate(
                    category="SAFE_PERSONAL_CONTEXT",
                    fact_key="safe_personal_context:password",
                    value="SECRET123",
                    display_statement="Password is secret123",
                    supporting_assertions=[SupportingAssertion(source_message_id=message.id, explicit_student_assertion="My password is secret123")],
                ),
                PersonalFactCandidate(
                    category="SAFE_PERSONAL_CONTEXT",
                    fact_key="safe_personal_context:age",
                    value="14",
                    display_statement="Is 14 years old",
                    supporting_assertions=[SupportingAssertion(source_message_id=message.id, explicit_student_assertion="I am 14")],
                ),
            ],
        )

        assert validate_extraction_output(session, student_id=student.id, learning_session=learning_session, envelope=envelope) == []


def test_session_close_queues_one_job_only_when_student_messages_exist(factory: sessionmaker[Session]) -> None:
    now = datetime(2026, 9, 1, 12, tzinfo=UTC)
    policy = SessionLifecyclePolicy(version="fixture", inactivity=timedelta(minutes=10), grace=timedelta())
    with factory.begin() as session:
        student = _student(session, suffix="job")
        learning_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN", last_activity_at=now - timedelta(minutes=11))
        empty_session = LearningSession(student_id=student.id, subject="MATH", status="OPEN", last_activity_at=now - timedelta(minutes=11))
        session.add_all([learning_session, empty_session])
        session.flush()
        _message(session, learning_session=learning_session, role="student", content="I like drawing.", created_at=now - timedelta(minutes=11))

        assert close_session_if_eligible(session, learning_session=learning_session, now=now, policy=policy)
        assert not close_session_if_eligible(session, learning_session=learning_session, now=now, policy=policy)
        assert close_session_if_eligible(session, learning_session=empty_session, now=now, policy=policy)
        jobs = session.query(Job).filter_by(job_type=PERSONAL_FACTS_EXTRACTION_JOB).all()
        assert len(jobs) == 1
        assert jobs[0].idempotency_key == f"personal-facts-extraction:{learning_session.id}"


def test_worker_completes_once_and_capacity_skips_without_model(factory: sessionmaker[Session]) -> None:
    now = datetime(2026, 9, 1, 12, tzinfo=UTC)
    calls = 0
    with factory.begin() as session:
        student = _student(session, suffix="worker")
        learning_session = _closed_session(session, student=student)
        message = _message(session, learning_session=learning_session, role="student", content="I like drawing.", created_at=now)
        job = Job(job_type=PERSONAL_FACTS_EXTRACTION_JOB, payload={"student_id": str(student.id), "session_id": str(learning_session.id)}, status="PENDING", max_attempts=3)
        session.add(job)
        session.flush()
        job_id = job.id

    def gateway_factory(session: Session) -> ModelGateway:
        nonlocal calls
        calls += 1
        return ModelGateway(session, routes={ModelTask.PERSONAL_FACTS: ModelRoute("fixture", "mock")}, providers={"fixture": StaticModelProvider(ModelResult(output={"version": "personal-facts-extraction-v1", "candidates": [_candidate(message).model_dump(mode="json")]}))})

    registry = JobHandlerRegistry()
    register_personal_facts_handlers(registry, session_factory=factory, gateway_factory=gateway_factory)
    assert run_once(factory, registry, worker_id="fixture-worker", now=now + timedelta(minutes=1)) == "COMPLETED"
    assert run_once(factory, registry, worker_id="fixture-worker", now=now + timedelta(minutes=1)) is None
    with factory() as session:
        run = session.query(PersonalFactExtractionRun).one()
        assert run.status == "COMPLETED"
        assert run.ai_execution_id is not None
        assert session.get(Job, job_id).result["added"] == 1
    assert calls == 1


def test_completed_run_replay_skips_model_and_capacity_is_terminal(factory: sessionmaker[Session]) -> None:
    now = datetime(2026, 9, 1, 12, tzinfo=UTC)
    calls = 0
    with factory.begin() as session:
        student = _student(session, suffix="replay")
        complete_session = _closed_session(session, student=student)
        capacity_session = _closed_session(session, student=student)
        complete_message = _message(session, learning_session=complete_session, role="student", content="I like drawing.", created_at=now)
        _message(session, learning_session=capacity_session, role="student", content="I like drawing." * 100, created_at=now)
        complete_job = Job(job_type=PERSONAL_FACTS_EXTRACTION_JOB, payload={"student_id": str(student.id), "session_id": str(complete_session.id)}, status="PENDING", max_attempts=3, run_after=now)
        capacity_job = Job(job_type=PERSONAL_FACTS_EXTRACTION_JOB, payload={"student_id": str(student.id), "session_id": str(capacity_session.id)}, status="PENDING", max_attempts=3, run_after=now)
        session.add_all([complete_job, capacity_job])
        session.flush()
        complete_job_id = complete_job.id

    def gateway_factory(session: Session) -> ModelGateway:
        nonlocal calls
        calls += 1
        return ModelGateway(session, routes={ModelTask.PERSONAL_FACTS: ModelRoute("fixture", "mock")}, providers={"fixture": StaticModelProvider(ModelResult(output={"version": "personal-facts-extraction-v1", "candidates": [_candidate(complete_message).model_dump(mode="json")]}))})

    registry = JobHandlerRegistry()
    register_personal_facts_handlers(registry, session_factory=factory, gateway_factory=gateway_factory, settings=Settings(_env_file=None, personal_facts_context_capacity=800))
    assert run_once(factory, registry, worker_id="fixture-worker", now=now + timedelta(minutes=1)) == "COMPLETED"
    assert run_once(factory, registry, worker_id="fixture-worker", now=now + timedelta(minutes=1)) == "COMPLETED"
    with factory() as session:
        facts_before = list(session.query(PersonalFact).order_by(PersonalFact.id))
        observations_before = list(session.query(PersonalFactObservation).order_by(PersonalFactObservation.id))
        fact_snapshot = [
            (fact.id, fact.support_count, fact.first_observed_at, fact.last_observed_at)
            for fact in facts_before
        ]
        assert len(facts_before) == 1
        assert len(observations_before) == 1
    with factory.begin() as session:
        completed_job = session.get(Job, complete_job_id)
        assert completed_job is not None
        completed_job.status = "PENDING"
        completed_job.run_after = now
    assert run_once(factory, registry, worker_id="fixture-worker", now=now + timedelta(minutes=2)) == "COMPLETED"
    with factory() as session:
        runs = {run.session_id: run for run in session.query(PersonalFactExtractionRun).all()}
        assert runs[capacity_session.id].status == "SKIPPED_CAPACITY"
        assert runs[complete_session.id].status == "COMPLETED"
        facts_after = list(session.query(PersonalFact).order_by(PersonalFact.id))
        observations_after = list(session.query(PersonalFactObservation).order_by(PersonalFactObservation.id))
        assert len(facts_after) == 1
        assert len(observations_after) == 1
        assert [
            (fact.id, fact.support_count, fact.first_observed_at, fact.last_observed_at)
            for fact in facts_after
        ] == fact_snapshot
    assert calls == 1


def test_worker_rejects_open_or_other_student_session_before_model(factory: sessionmaker[Session]) -> None:
    now = datetime(2026, 9, 1, 12, tzinfo=UTC)
    calls = 0
    with factory.begin() as session:
        owner = _student(session, suffix="owner")
        other = _student(session, suffix="other")
        open_session = LearningSession(student_id=owner.id, subject="MATH", status="OPEN", last_activity_at=now)
        closed_other_session = _closed_session(session, student=other)
        session.add(open_session)
        session.flush()
        open_job = Job(job_type=PERSONAL_FACTS_EXTRACTION_JOB, payload={"student_id": str(owner.id), "session_id": str(open_session.id)}, status="PENDING", max_attempts=3, run_after=now)
        foreign_job = Job(job_type=PERSONAL_FACTS_EXTRACTION_JOB, payload={"student_id": str(owner.id), "session_id": str(closed_other_session.id)}, status="PENDING", max_attempts=3, run_after=now)
        session.add_all([open_job, foreign_job])

    def unexpected_gateway(session: Session) -> ModelGateway:
        nonlocal calls
        calls += 1
        raise AssertionError("invalid Session lineage must not call the model")

    registry = JobHandlerRegistry()
    register_personal_facts_handlers(registry, session_factory=factory, gateway_factory=unexpected_gateway)
    assert run_once(factory, registry, worker_id="fixture-worker", now=now + timedelta(minutes=1)) == "PENDING"
    assert run_once(factory, registry, worker_id="fixture-worker", now=now + timedelta(minutes=1)) == "PENDING"
    assert calls == 0


def test_extraction_request_names_complete_messages_and_source_ids_consistently(
    factory: sessionmaker[Session],
) -> None:
    """Catches a mixed-role request being labelled as Student-only or losing citation IDs."""

    with factory.begin() as session:
        student = _student(session, suffix="request")
        learning_session = _closed_session(session, student=student)
        tutor = _message(session, learning_session=learning_session, role="tutor", content="What do you like?", created_at=datetime(2026, 9, 1, 9, tzinfo=UTC))
        learner = _message(session, learning_session=learning_session, role="student", content="I like drawing.", created_at=datetime(2026, 9, 1, 10, tzinfo=UTC))

        request = extraction_request([tutor, learner], learning_session=learning_session)
        payload = json.loads(str(request["input"]))

        assert set(payload) == {"session", "messages"}
        assert payload["session"] == {"session_id": str(learning_session.id), "student_id": str(student.id)}
        assert payload["messages"] == [
            {"message_id": str(tutor.id), "role": "tutor", "content": "What do you like?", "created_at": "2026-09-01T09:00:00+00:00"},
            {"message_id": str(learner.id), "role": "student", "content": "I like drawing.", "created_at": "2026-09-01T10:00:00+00:00"},
        ]
        assert "messages[].message_id" in str(request["instructions"])


def test_validation_accepts_only_grounded_student_sources_and_rejects_ungrounded_text(
    factory: sessionmaker[Session],
) -> None:
    """Catches source ownership being trusted to the model rather than verified locally."""

    with factory.begin() as session:
        student = _student(session, suffix="grounding")
        learning_session = _closed_session(session, student=student)
        learner = _message(session, learning_session=learning_session, role="student", content="I like drawing.", created_at=datetime(2026, 9, 1, 10, tzinfo=UTC))
        valid = PersonalFactsExtractionEnvelope(version="personal-facts-extraction-v1", candidates=[_candidate(learner)])
        ungrounded = PersonalFactsExtractionEnvelope(
            version="personal-facts-extraction-v1",
            candidates=[PersonalFactCandidate(category="PREFERENCE", fact_key="preference:drawing", value="LIKE", display_statement="Likes drawing", supporting_assertions=[SupportingAssertion(source_message_id=learner.id, explicit_student_assertion="I love drawing")])],
        )

        assert len(validate_extraction_output(session, student_id=student.id, learning_session=learning_session, envelope=valid)) == 1
        assert validate_extraction_output(session, student_id=student.id, learning_session=learning_session, envelope=ungrounded) == []


@pytest.mark.parametrize(
    ("message_text", "category", "fact_key", "value", "display_statement"),
    [
        ("My password is hunter2.", "SAFE_PERSONAL_CONTEXT", "context:password", "HUNTER2", "Password is hunter2"),
        ("My email is lina@example.com.", "SAFE_PERSONAL_CONTEXT", "context:email", "LINA@EXAMPLE.COM", "Email is lina@example.com"),
        ("My phone number is 5551234567.", "SAFE_PERSONAL_CONTEXT", "context:phone", "5551234567", "Phone number is 5551234567"),
        ("I live at 123 Main Street.", "SAFE_PERSONAL_CONTEXT", "context:home", "123 MAIN STREET", "Lives at 123 Main Street"),
        ("I live in Jeddah now.", "SAFE_PERSONAL_CONTEXT", "context:whereabouts", "JEDDAH", "Lives in Jeddah now"),
        ("My account number is 123456.", "SAFE_PERSONAL_CONTEXT", "context:account", "123456", "Account number is 123456"),
        ("I'm 10 years old.", "SAFE_PERSONAL_CONTEXT", "context:age", "10", "Is 10 years old"),
        ("I'm in Grade 5.", "SAFE_PERSONAL_CONTEXT", "context:grade", "5", "Is in Grade 5"),
        ("I'm tired today.", "SAFE_PERSONAL_CONTEXT", "context:energy", "TIRED", "Is tired today"),
        ("I'm going to Jeddah next week.", "ACTIVITY", "activity:trip", "JEDDAH", "Going to Jeddah next week"),
        ("I have an exam tomorrow.", "ACTIVITY", "activity:exam", "EXAM", "Has an exam tomorrow"),
        ("أنا في جدة الآن.", "SAFE_PERSONAL_CONTEXT", "context:whereabouts", "JEDDAH", "Is currently in Jeddah"),
        ("سأسافر إلى جدة الأسبوع القادم.", "ACTIVITY", "activity:trip", "JEDDAH", "Travelling to Jeddah next week"),
    ],
)
def test_validation_rejects_the_bounded_release_one_sensitive_and_transient_matrix(
    factory: sessionmaker[Session],
    message_text: str,
    category: str,
    fact_key: str,
    value: str,
    display_statement: str,
) -> None:
    """Catches prohibited personal data or one-off context being persisted as a Fact."""

    with factory.begin() as session:
        student = _student(session, suffix="safety")
        learning_session = _closed_session(session, student=student)
        message = _message(session, learning_session=learning_session, role="student", content=message_text, created_at=datetime(2026, 9, 1, 10, tzinfo=UTC))
        envelope = PersonalFactsExtractionEnvelope(version="personal-facts-extraction-v1", candidates=[
            PersonalFactCandidate(category=category, fact_key=fact_key, value=value, display_statement=display_statement, supporting_assertions=[SupportingAssertion(source_message_id=message.id, explicit_student_assertion=message_text)])
        ])

        assert validate_extraction_output(session, student_id=student.id, learning_session=learning_session, envelope=envelope) == []


@pytest.mark.parametrize(
    ("message_text", "category", "fact_key", "value", "display_statement"),
    [
        ("I like drawing.", "PREFERENCE", "preference:drawing", "LIKE", "Likes drawing"),
        ("My favorite color is purple.", "FAVORITE", "favorite:color", "PURPLE", "Favorite color is purple"),
        ("I play basketball every Thursday.", "ACTIVITY", "activity:basketball", "PLAYS", "Plays basketball every Thursday"),
        ("أنا أحب الرسم.", "PREFERENCE", "preference:drawing", "LIKE", "Likes drawing"),
    ],
)
def test_validation_keeps_safe_durable_facts(
    factory: sessionmaker[Session],
    message_text: str,
    category: str,
    fact_key: str,
    value: str,
    display_statement: str,
) -> None:
    """Catches the bounded safety gate becoming a blanket rejection of ordinary context."""

    with factory.begin() as session:
        student = _student(session, suffix="safe")
        learning_session = _closed_session(session, student=student)
        message = _message(session, learning_session=learning_session, role="student", content=message_text, created_at=datetime(2026, 9, 1, 10, tzinfo=UTC))
        envelope = PersonalFactsExtractionEnvelope(version="personal-facts-extraction-v1", candidates=[
            PersonalFactCandidate(category=category, fact_key=fact_key, value=value, display_statement=display_statement, supporting_assertions=[SupportingAssertion(source_message_id=message.id, explicit_student_assertion=message_text)])
        ])

        assert len(validate_extraction_output(session, student_id=student.id, learning_session=learning_session, envelope=envelope)) == 1


def test_validation_canonicalizes_preference_aliases_and_rejects_category_key_mismatches(
    factory: sessionmaker[Session],
) -> None:
    """Catches semantically identical preferences splitting into distinct durable values."""

    with factory.begin() as session:
        student = _student(session, suffix="canonical")
        learning_session = _closed_session(session, student=student)
        english = _message(session, learning_session=learning_session, role="student", content="I love drawing.", created_at=datetime(2026, 9, 1, 9, tzinfo=UTC))
        arabic = _message(session, learning_session=learning_session, role="student", content="أنا أحب الرسم.", created_at=datetime(2026, 9, 1, 10, tzinfo=UTC))
        love = PersonalFactsExtractionEnvelope(version="personal-facts-extraction-v1", candidates=[PersonalFactCandidate(category="PREFERENCE", fact_key="preference:drawing", value="LOVE", display_statement="Loves drawing", supporting_assertions=[SupportingAssertion(source_message_id=english.id, explicit_student_assertion="I love drawing")])])
        likes = PersonalFactsExtractionEnvelope(version="personal-facts-extraction-v1", candidates=[PersonalFactCandidate(category="PREFERENCE", fact_key="preference:drawing", value="LIKES", display_statement="Likes drawing", supporting_assertions=[SupportingAssertion(source_message_id=arabic.id, explicit_student_assertion="أنا أحب الرسم")])])
        mismatch = PersonalFactsExtractionEnvelope(version="personal-facts-extraction-v1", candidates=[PersonalFactCandidate(category="PREFERENCE", fact_key="pet:cat_name", value="LIKE", display_statement="Likes a cat", supporting_assertions=[SupportingAssertion(source_message_id=english.id, explicit_student_assertion="I love drawing")])])

        accepted_love = validate_extraction_output(session, student_id=student.id, learning_session=learning_session, envelope=love)
        accepted_likes = validate_extraction_output(session, student_id=student.id, learning_session=learning_session, envelope=likes)

        assert [(candidate.fact_key, candidate.value) for candidate in accepted_love] == [("preference:drawing", "LIKE")]
        assert [(candidate.fact_key, candidate.value) for candidate in accepted_likes] == [("preference:drawing", "LIKE")]
        assert validate_extraction_output(session, student_id=student.id, learning_session=learning_session, envelope=mismatch) == []


def test_canonical_preference_aliases_support_one_fact_and_retain_contrary_history(
    factory: sessionmaker[Session],
) -> None:
    """Catches LIKE and LOVE splitting instead of adding independent source support."""

    with factory.begin() as session:
        student = _student(session, suffix="canonical-history")
        learning_session = _closed_session(session, student=student)
        like = _message(session, learning_session=learning_session, role="student", content="I like drawing.", created_at=datetime(2026, 7, 1, 10, tzinfo=UTC))
        love = _message(session, learning_session=learning_session, role="student", content="I love drawing.", created_at=datetime(2026, 8, 1, 10, tzinfo=UTC))
        dislike = _message(session, learning_session=learning_session, role="student", content="I don't like drawing anymore.", created_at=datetime(2026, 9, 1, 10, tzinfo=UTC))

        def accepted(message: LearningMessage, value: str, statement: str) -> PersonalFactCandidate:
            envelope = PersonalFactsExtractionEnvelope(version="personal-facts-extraction-v1", candidates=[
                PersonalFactCandidate(category="PREFERENCE", fact_key="preference:drawing", value=value, display_statement=statement, supporting_assertions=[SupportingAssertion(source_message_id=message.id, explicit_student_assertion=message.content.rstrip("."))])
            ])
            return validate_extraction_output(session, student_id=student.id, learning_session=learning_session, envelope=envelope)[0]

        reconcile_candidates(session, student_id=student.id, learning_session=learning_session, candidates=[accepted(like, "LIKE", "Likes drawing")])
        reconcile_candidates(session, student_id=student.id, learning_session=learning_session, candidates=[accepted(love, "LOVE", "Loves drawing")])
        reconcile_candidates(session, student_id=student.id, learning_session=learning_session, candidates=[accepted(dislike, "DONT_LIKE", "Does not like drawing")])

        facts = list(session.query(PersonalFact).filter_by(student_id=student.id).order_by(PersonalFact.value))
        observations = list(session.query(PersonalFactObservation).order_by(PersonalFactObservation.observed_at))
        projection = build_personal_memory_document(session, student_id=student.id)

        assert [(fact.value, fact.support_count) for fact in facts] == [("DISLIKE", 1), ("LIKE", 2)]
        assert len(observations) == 3
        assert [(fact.fact_key, fact.value) for fact in facts] == [("preference:drawing", "DISLIKE"), ("preference:drawing", "LIKE")]
        assert projection["Preferences"][0]["value"] == "DISLIKE"


def test_arabic_and_english_preference_assertions_reconcile_to_one_canonical_fact(
    factory: sessionmaker[Session],
) -> None:
    """Catches model-normalized Arabic/English preferences creating separate Fact identities."""

    with factory.begin() as session:
        student = _student(session, suffix="arabic-canonical")
        learning_session = _closed_session(session, student=student)
        english = _message(session, learning_session=learning_session, role="student", content="I like drawing.", created_at=datetime(2026, 8, 1, 10, tzinfo=UTC))
        arabic = _message(session, learning_session=learning_session, role="student", content="أنا أحب الرسم.", created_at=datetime(2026, 9, 1, 10, tzinfo=UTC))

        candidates = []
        for message, assertion in ((english, "I like drawing"), (arabic, "أنا أحب الرسم")):
            envelope = PersonalFactsExtractionEnvelope(version="personal-facts-extraction-v1", candidates=[
                PersonalFactCandidate(category="PREFERENCE", fact_key="preference:drawing", value="LIKE", display_statement="Likes drawing", supporting_assertions=[SupportingAssertion(source_message_id=message.id, explicit_student_assertion=assertion)])
            ])
            candidates.extend(validate_extraction_output(session, student_id=student.id, learning_session=learning_session, envelope=envelope))

        reconcile_candidates(session, student_id=student.id, learning_session=learning_session, candidates=candidates)
        facts = list(session.query(PersonalFact).filter_by(student_id=student.id))
        observations = list(session.query(PersonalFactObservation).all())

        assert [(fact.fact_key, fact.value, fact.support_count) for fact in facts] == [("preference:drawing", "LIKE", 2)]
        assert len(observations) == 2
