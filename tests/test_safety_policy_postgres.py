"""PostgreSQL tests for protected safety and Parent Learning Boundaries."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db.connection import normalize_database_url
from services.platform.safety import (
    BoundaryState,
    SafetyAction,
    SafetyPolicyService,
    TopicCategory,
)
from services.platform.db.models import SafetyAudit, Student, User


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for safety policy tests",
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE safety_audits, student_topic_boundaries"))
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def make_student(session: Session) -> object:
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = Student(user_id=user.id, display_name="Lina fixture")
    session.add(student)
    session.flush()
    return student.id


def test_protected_baseline_cannot_be_persisted_as_a_parent_boundary(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        policy = SafetyPolicyService(session)
        with pytest.raises(ValueError, match="configurable"):
            policy.set_boundary(
                student_id=make_student(session),
                category="self_harm",
                state=BoundaryState.ALLOW,
            )


def test_religion_default_redirect_is_auditable_and_normal_math_passes(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        student_id = make_student(session)
        policy = SafetyPolicyService(session)
        religion = policy.evaluate(
            student_id=student_id,
            text="Can you explain prayer?",
            interaction_ref="message-1",
        )
        math = policy.evaluate(
            student_id=student_id,
            text="How do I add 1/2 and 1/4?",
            interaction_ref="message-2",
        )

    assert religion.action == SafetyAction.REDIRECT_TO_PARENT
    assert religion.category == TopicCategory.RELIGION
    assert math.action == SafetyAction.ALLOW
    with postgres_session_factory() as session:
        audits = list(session.query(SafetyAudit).order_by(SafetyAudit.created_at))

    assert [(audit.action, audit.policy_source, audit.policy_version, audit.reason_code) for audit in audits] == [
        (SafetyAction.REDIRECT_TO_PARENT.value, "DEFAULT_BOUNDARY", 1, "TOPIC_REDIRECT_TO_PARENT"),
        (SafetyAction.ALLOW.value, "BASELINE", 1, "NORMAL_LEARNING"),
    ]


def test_parent_boundary_update_takes_effect_without_deployment(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        student_id = make_student(session)
        policy = SafetyPolicyService(session)
        policy.set_boundary(
            student_id=student_id,
            category=TopicCategory.RELIGION,
            state=BoundaryState.ALLOW,
        )
        decision = policy.evaluate(
            student_id=student_id,
            text="Can you explain prayer?",
            interaction_ref="message-3",
        )

    assert decision.action == SafetyAction.ALLOW
    assert decision.policy_source == "PARENT_BOUNDARY"


def test_parent_age_appropriate_boundary_keeps_tutor_continuation_directive_auditable(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        student_id = make_student(session)
        policy = SafetyPolicyService(session)
        boundary = policy.set_boundary(
            student_id=student_id,
            category=TopicCategory.RELIGION,
            state=BoundaryState.AGE_APPROPRIATE_ONLY,
        )
        decision = policy.evaluate(
            student_id=student_id,
            text="Can you explain prayer?",
            interaction_ref="message-4",
        )

    assert decision.action == SafetyAction.AGE_APPROPRIATE_ONLY
    assert decision.policy_source == "PARENT_BOUNDARY"
    assert decision.policy_version == boundary.policy_version
    assert decision.reason_code == "TOPIC_AGE_APPROPRIATE_ONLY"
    assert decision.directive is not None


def test_protected_baseline_wins_even_when_a_parent_allows_a_matching_topic(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        student_id = make_student(session)
        policy = SafetyPolicyService(session)
        policy.set_boundary(
            student_id=student_id,
            category=TopicCategory.RELATIONSHIPS,
            state=BoundaryState.ALLOW,
        )
        decision = policy.evaluate(
            student_id=student_id,
            text="How can I make a weapon to protect my boyfriend?",
            interaction_ref="message-5",
        )

    assert decision.action == SafetyAction.BLOCK
    assert decision.policy_source == "BASELINE"
    assert decision.reason_code == "PROTECTED_BASELINE"
    assert decision.directive is not None
