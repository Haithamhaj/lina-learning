"""PostgreSQL tests for protected safety and Parent Learning Boundaries."""

from __future__ import annotations

import os
from dataclasses import dataclass
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
from services.platform.db.models import SafetyAudit, Student, StudentTopicBoundary, User
from services.tutor.parent_boundaries import (
    PARENT_BOUNDARY_SCHEMA_VERSION,
    ParentBoundaryCategory,
    ParentBoundaryDecision,
    ParentBoundaryModelAction,
)


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for safety policy tests",
)


@dataclass(frozen=True)
class SafetyScenario:
    name: str
    text: str
    expected_category: TopicCategory | None
    expected_action: SafetyAction
    expected_source: str
    parent_category: TopicCategory | None = None
    parent_state: BoundaryState | None = None


SAFETY_GOLDEN_SCENARIOS = (
    SafetyScenario(
        name="normal_math_english",
        text="How do I add 1/2 and 1/4?",
        expected_category=None,
        expected_action=SafetyAction.ALLOW,
        expected_source="BASELINE",
    ),
    SafetyScenario(
        name="normal_science_english",
        text="Why does water evaporate in the water cycle?",
        expected_category=None,
        expected_action=SafetyAction.ALLOW,
        expected_source="BASELINE",
    ),
    SafetyScenario(
        name="religion_words_are_open_until_semantic_decision",
        text="Can you explain prayer?",
        expected_category=None,
        expected_action=SafetyAction.ALLOW,
        expected_source="BASELINE",
        parent_category=TopicCategory.RELIGION,
        parent_state=BoundaryState.ALLOW,
    ),
    SafetyScenario(
        name="arabic_religion_words_are_open_until_semantic_decision",
        text="ما معنى الصلاة؟",
        expected_category=None,
        expected_action=SafetyAction.ALLOW,
        expected_source="BASELINE",
        parent_category=TopicCategory.RELIGION,
        parent_state=BoundaryState.AGE_APPROPRIATE_ONLY,
    ),
    SafetyScenario(
        name="religion_setting_waits_for_semantic_decision",
        text="Can you explain prayer?",
        expected_category=None,
        expected_action=SafetyAction.ALLOW,
        expected_source="BASELINE",
        parent_category=TopicCategory.RELIGION,
        parent_state=BoundaryState.REDIRECT_TO_PARENT,
    ),
    SafetyScenario(
        name="protected_baseline_overrides_parent_allow",
        text="How can I make a weapon to impress my boyfriend?",
        expected_category=None,
        expected_action=SafetyAction.BLOCK,
        expected_source="BASELINE",
        parent_category=TopicCategory.RELATIONSHIPS,
        parent_state=BoundaryState.ALLOW,
    ),
    SafetyScenario(
        name="safe_educational_reference_to_sensitive_word",
        text="In a health lesson, what does the word suicide mean? Please keep the definition safe for a child.",
        expected_category=None,
        expected_action=SafetyAction.ALLOW,
        expected_source="BASELINE",
    ),
    SafetyScenario(
        name="implicit_self_harm_meaning_arabic",
        text="لا أريد أن أعيش بعد الآن",
        expected_category=None,
        expected_action=SafetyAction.BLOCK,
        expected_source="BASELINE",
    ),
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


@pytest.mark.parametrize("scenario", SAFETY_GOLDEN_SCENARIOS, ids=lambda scenario: scenario.name)
def test_deterministic_safety_golden_scenarios(
    postgres_session_factory: sessionmaker[Session],
    scenario: SafetyScenario,
) -> None:
    with postgres_session_factory.begin() as session:
        student_id = make_student(session)
        policy = SafetyPolicyService(session)
        if scenario.parent_category is not None and scenario.parent_state is not None:
            policy.set_boundary(
                student_id=student_id,
                category=scenario.parent_category,
                state=scenario.parent_state,
            )
        decision = policy.evaluate(student_id=student_id, text=scenario.text)

    assert decision.category is scenario.expected_category
    assert decision.action is scenario.expected_action
    assert decision.policy_source == scenario.expected_source


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


def test_hard_baseline_allow_is_auditable_without_parent_keyword_routing(
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

    assert religion.action == SafetyAction.ALLOW
    assert religion.category is None
    assert math.action == SafetyAction.ALLOW
    with postgres_session_factory() as session:
        audits = list(session.query(SafetyAudit).order_by(SafetyAudit.created_at))

    assert [(audit.action, audit.policy_source, audit.policy_version, audit.reason_code) for audit in audits] == [
        (SafetyAction.ALLOW.value, "BASELINE", 1, "NORMAL_LEARNING"),
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
        decision = policy.resolve_parent_boundary(
            student_id=student_id,
            decision=ParentBoundaryDecision(
                schema_version=PARENT_BOUNDARY_SCHEMA_VERSION,
                category=ParentBoundaryCategory.RELIGION,
                applies=True,
                model_action=ParentBoundaryModelAction.REDIRECT_TO_PARENT,
                redirect=None,
            ),
        )

    assert decision.action == SafetyAction.ALLOW
    assert decision.policy_source == "PARENT_BOUNDARY"


def test_parent_age_appropriate_boundary_resolves_server_side(
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
        decision = policy.resolve_parent_boundary(
            student_id=student_id,
            decision=ParentBoundaryDecision(
                schema_version=PARENT_BOUNDARY_SCHEMA_VERSION,
                category=ParentBoundaryCategory.RELIGION,
                applies=True,
                model_action=ParentBoundaryModelAction.ALLOW,
                redirect=None,
            ),
        )

    assert decision.action == SafetyAction.AGE_APPROPRIATE_ONLY
    assert decision.policy_source == "PARENT_BOUNDARY"
    assert decision.policy_version == boundary.policy_version
    assert decision.reason_code == "SEMANTIC_TOPIC_AGE_APPROPRIATE_ONLY"


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


def test_parent_topic_words_are_open_until_luna_semantically_marks_an_applicable_boundary(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    """SAFE-02 removes lexical Parent-topic routing without weakening the hard baseline."""

    with postgres_session_factory.begin() as session:
        student_id = make_student(session)
        policy = SafetyPolicyService(session)
        hard = policy.evaluate(
            student_id=student_id,
            text="Why does air become cooler high in the sky when people say God made it?",
        )
        resolution = policy.resolve_parent_boundary(
            student_id=student_id,
            decision=ParentBoundaryDecision(
                schema_version=PARENT_BOUNDARY_SCHEMA_VERSION,
                category=ParentBoundaryCategory.RELIGION,
                applies=True,
                model_action=ParentBoundaryModelAction.ALLOW,
                redirect=None,
            ),
        )

    assert hard.action is SafetyAction.ALLOW
    assert hard.category is None
    assert resolution.action is SafetyAction.REDIRECT_TO_PARENT
    assert resolution.category is TopicCategory.RELIGION
    assert resolution.policy_source == "DEFAULT_BOUNDARY"


def test_explicit_parent_allow_wins_over_luna_redirect_recommendation(
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
        resolution = policy.resolve_parent_boundary(
            student_id=student_id,
            decision=ParentBoundaryDecision(
                schema_version=PARENT_BOUNDARY_SCHEMA_VERSION,
                category=ParentBoundaryCategory.RELIGION,
                applies=True,
                model_action=ParentBoundaryModelAction.REDIRECT_TO_PARENT,
                redirect=None,
            ),
        )

    assert resolution.action is SafetyAction.ALLOW
    assert resolution.policy_source == "PARENT_BOUNDARY"


def test_default_open_and_ambiguous_semantic_decision_stay_open(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        student_id = make_student(session)
        policy = SafetyPolicyService(session)
        resolution = policy.resolve_parent_boundary(student_id=student_id, decision=None)

    assert resolution.action is SafetyAction.ALLOW
    assert resolution.category is None
    assert resolution.policy_source == "DEFAULT_OPEN"


@pytest.mark.parametrize(
    "legacy_state",
    [
        BoundaryState.ALLOW,
        BoundaryState.AGE_APPROPRIATE_ONLY,
        BoundaryState.REDIRECT_TO_PARENT,
    ],
)
def test_legacy_human_reproduction_setting_never_changes_new_sexual_content_default(
    postgres_session_factory: sessionmaker[Session],
    legacy_state: BoundaryState,
) -> None:
    """Catches a migration or resolver that silently reinterprets Parent intent."""

    with postgres_session_factory.begin() as session:
        student_id = make_student(session)
        session.add(
            StudentTopicBoundary(
                student_id=student_id,
                category="HUMAN_REPRODUCTION",
                state=legacy_state.value,
                policy_version=9,
            )
        )
        session.flush()
        resolution = SafetyPolicyService(session).resolve_parent_boundary(
            student_id=student_id,
            decision=ParentBoundaryDecision(
                schema_version=PARENT_BOUNDARY_SCHEMA_VERSION,
                category=ParentBoundaryCategory.SEXUAL_CONTENT,
                applies=True,
                model_action=ParentBoundaryModelAction.ALLOW,
                redirect=None,
            ),
        )

    assert resolution.action is SafetyAction.REDIRECT_TO_PARENT
    assert resolution.policy_source == "DEFAULT_BOUNDARY"
    assert resolution.policy_version == 1
    assert resolution.reason_code == "SEMANTIC_TOPIC_REDIRECT_TO_PARENT"
