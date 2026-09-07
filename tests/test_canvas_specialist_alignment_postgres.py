"""CS-03 PostgreSQL persistence and zero-side-effect contracts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete, StreamDelta
from services.platform.core_profile import StudentCoreContext
from services.platform.db import models as m
from services.platform.db.connection import normalize_database_url
from services.platform.safety import SafetyAction, SafetyDecision
from services.retrieval.service import RetrievedBlock
from services.tutor.context import SessionContextMessage, TutorContext, TutorContextDebug
from services.tutor.context import TutorContextBuilder
from services.tutor.runtime import TutorRuntime
import services.tutor.context as tutor_context_module


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL is required for CS-03 persistence tests"
)


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text(
            "TRUNCATE jobs, studio_canvas_specialist_runs, studio_events, studio_snapshots, studio_scenes, "
            "studio_runtimes, candidate_events, learning_evidence, learning_events, current_learning_states, "
            "learner_patterns, learner_intelligence_cards, personal_fact_observations, personal_fact_extraction_runs, "
            "personal_facts, learning_messages, learning_segments, ai_executions, learning_sessions, students, users CASCADE"
        ))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _learning_session(session: Session) -> m.LearningSession:
    user = m.User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user)
    session.flush()
    student = m.Student(user_id=user.id, display_name="Lina")
    session.add(student)
    session.flush()
    learning_session = m.LearningSession(student_id=student.id, subject="SCIENCE", status="OPEN")
    session.add(learning_session)
    session.flush()
    return learning_session


class _ContextBuilder:
    def __init__(self, catalogue: tuple[dict[str, str], ...] = (), *, catalogue_status: str = "AVAILABLE") -> None:
        self._catalogue = catalogue
        self._catalogue_status = catalogue_status

    def build(
        self,
        *,
        learning_session: m.LearningSession,
        question: str,
        current_turn_message_id: UUID | None = None,
        **_: object,
    ) -> TutorContext:
        message_id = current_turn_message_id or uuid4()
        block = RetrievedBlock(
            text="A larva becomes a pupa before an adult emerges.", source_ref="book#butterfly",
            page_number=12, block_type="EXPLANATION", score=1.0, semantic_key="butterfly",
            semantic_type="PROCESS", concept_key="life-cycle", source_refs=("book#butterfly",),
            page_numbers=(12,), matched=True,
        )
        return TutorContext(
            question=question, subject="SCIENCE", grade_level=5, focus=None,
            session_messages=(SessionContextMessage(message_id, "student", question),), retrieval=(block,), intelligence=(),
            debug=TutorContextDebug(
                None, (message_id,), ("book#butterfly",), (), (), current_turn_message_id=message_id,
                visual_personalization_catalog_status=self._catalogue_status,
            ),
            student_core_context=StudentCoreContext("Lina", 10, 5),
            visual_personalization_catalog=self._catalogue,
        )


class _Policy:
    def __init__(self, action: SafetyAction = SafetyAction.ALLOW) -> None:
        self._action = action

    def evaluate(self, **_: object) -> SafetyDecision:
        return SafetyDecision(self._action, None, "BASELINE", 1, "TEST", "normal", None)


class _Provider:
    def __init__(self, visual_order: object | None) -> None:
        self.calls = 0
        self._visual_order = visual_order

    def stream(self, route: ModelRoute, payload: dict[str, object]):
        del route, payload
        self.calls += 1
        output = {
            "text": "Let us follow the butterfly stages.", "suggested_actions": [], "guided_check": None,
            "teaching_mode": None, "teaching_strategy": None, "teaching_method_id": None,
            "prior_method_relation": None, "segment_relation": None, "structured_segment_state": None,
            "parent_boundary": None, "candidate_metadata": None, "provisional_broad_subject": None,
            "workspace_intent": None, "workspace_visual_order": self._visual_order,
        }
        yield StreamDelta(str(output["text"]))
        yield StreamComplete(ModelResult(output=output, input_tokens=4, output_tokens=3))


def _runtime(
    session: Session,
    visual_order: object | None,
    *,
    action: SafetyAction = SafetyAction.ALLOW,
    catalogue: tuple[dict[str, str], ...] = (),
    catalogue_status: str = "AVAILABLE",
) -> tuple[TutorRuntime, _Provider]:
    provider = _Provider(visual_order)
    return TutorRuntime(
        session,
        context_builder=_ContextBuilder(catalogue, catalogue_status=catalogue_status),
        safety_policy=_Policy(action),
        gateway=ModelGateway(session, routes={m.ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")}, providers={"fixture": provider}),
    ), provider


def _protected_counts(session: Session) -> tuple[int, ...]:
    return tuple(session.scalar(select(func.count()).select_from(model)) for model in (
        m.Job, m.StudioCanvasSpecialistRun, m.StudioScene, m.CandidateEvent, m.LearningEvent,
        m.LearningEvidence, m.CurrentLearningState, m.LearnerPattern, m.LearnerIntelligenceCard,
        m.PersonalFact, m.PersonalFactObservation,
    ))


def _order(**overrides: object) -> dict[str, object]:
    order: dict[str, object] = {
        "version": "workspace-visual-order-v1", "operation": "COMPOSE", "pattern": "PROCESS", "topology": "SEQUENCE",
        "objective": "Explain the butterfly life cycle.",
        "required_semantics": ["Egg becomes larva.", "Larva becomes pupa.", "Adult emerges."],
        "required_relations": ["Stages occur in this order."], "must_not_imply": ["The same adult returns to egg."],
        "source_references": ["book#butterfly"], "personal_fact_keys": ["favorite:butterfly"],
        "locale": "en", "direction": "ltr", "use_display_name": True,
    }
    order.update(overrides)
    return order


def _tutor_message(session: Session, learning_session: m.LearningSession) -> m.LearningMessage:
    return session.scalar(select(m.LearningMessage).where(
        m.LearningMessage.session_id == learning_session.id, m.LearningMessage.role == "tutor"
    ))


def _fact(session: Session, learning_session: m.LearningSession, *, key: str, category: str, statement: str, observed_at: datetime) -> m.PersonalFact:
    fact = m.PersonalFact(
        student_id=learning_session.student_id, category=category, fact_key=key, value=statement,
        display_statement=statement, support_count=1, first_observed_at=observed_at, last_observed_at=observed_at,
    )
    session.add(fact)
    return fact


def _catalogue(session: Session, learning_session: m.LearningSession) -> tuple[tuple[dict[str, str], ...], str]:
    return TutorContextBuilder(session, retrieval_service=object())._visual_personalization_catalog(  # noqa: SLF001
        learning_session=learning_session,
    )


def test_null_and_admitted_visual_orders_round_trip_with_one_automatic_specialist_admission(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        session.add(m.PersonalFact(
            student_id=learning_session.student_id, category="FAVORITE", fact_key="favorite:butterfly",
            value="butterfly", display_statement="Likes butterflies", support_count=1,
            first_observed_at=datetime.now(UTC), last_observed_at=datetime.now(UTC),
        ))
        session.flush()
        baseline = _protected_counts(session)
        runtime, provider = _runtime(session, None)
        list(runtime.stream_turn(learning_session=learning_session, question="Tell me about butterflies."))
        assert _tutor_message(session, learning_session).payload["workspace_visual"] == {
            "status": "NOT_REQUESTED", "reason_code": None, "admitted_order": None,
            "semantic_alignment": None, "order_digest": None, "frozen_composition_pack": None,
        }
        assert provider.calls == 1
        assert _protected_counts(session) == baseline

    with factory.begin() as session:
        learning_session = _learning_session(session)
        session.add(m.StudioRuntime(student_id=learning_session.student_id, learning_session_id=learning_session.id))
        session.add(m.PersonalFact(
            student_id=learning_session.student_id, category="FAVORITE", fact_key="favorite:butterfly",
            value="butterfly", display_statement="Likes butterflies", support_count=1,
            first_observed_at=datetime.now(UTC), last_observed_at=datetime.now(UTC),
        ))
        session.flush()
        baseline = _protected_counts(session)
        runtime, provider = _runtime(
            session,
            _order(),
            catalogue=(
                {"fact_key": "favorite:butterfly", "category": "FAVORITE", "display_statement": "Likes butterflies"},
            ),
        )
        list(runtime.stream_turn(learning_session=learning_session, question="How does a butterfly grow?"))
        session.flush()
        session.expire_all()
        visual = _tutor_message(session, learning_session).payload["workspace_visual"]
        pack = visual["frozen_composition_pack"]
        assert visual["status"] == "ADMITTED" and len(visual["order_digest"]) == 64
        assert visual["semantic_alignment"]["required_semantics"][0] == {"id": "F1", "statement": "Egg becomes larva."}
        assert pack["grounding"] == {"origin": "RETRIEVED_SOURCE", "excerpts": [{"source_ref": "book#butterfly", "text": "A larva becomes a pupa before an adult emerges."}]}
        assert pack["visual_learner_context"] == {
            "version": "visual-learner-context-v1", "core_profile": {"age_years": 10, "grade_level": 5, "display_name": "Lina"},
            "selected_personal_facts": [{"fact_key": "favorite:butterfly", "category": "FAVORITE", "display_statement": "Likes butterflies"}],
        }
        assert provider.calls == 1
        assert _protected_counts(session) == (
            baseline[0] + 1, baseline[1] + 1, *baseline[2:]
        )
        job = session.scalar(select(m.Job))
        run = session.scalar(select(m.StudioCanvasSpecialistRun))
        assert job is not None and job.max_attempts == 1
        assert run is not None and run.status == "PENDING" and run.job_id == job.id


def test_rejection_and_parent_redirect_persist_no_admitted_pack(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        baseline = _protected_counts(session)
        runtime, _ = _runtime(session, _order(source_references=["unauthorized#source"], personal_fact_keys=[]))
        list(runtime.stream_turn(learning_session=learning_session, question="Show the process."))
        visual = _tutor_message(session, learning_session).payload["workspace_visual"]
        assert visual["status"] == "REJECTED" and visual["reason_code"] == "SOURCE_REFERENCE_UNAUTHORIZED"
        assert visual["frozen_composition_pack"] is None and _protected_counts(session) == baseline

    with factory.begin() as session:
        learning_session = _learning_session(session)
        baseline = _protected_counts(session)
        runtime, provider = _runtime(session, _order(), action=SafetyAction.REDIRECT_TO_PARENT)
        list(runtime.stream_turn(learning_session=learning_session, question="A parent-boundary request."))
        visual = _tutor_message(session, learning_session).payload["workspace_visual"]
        assert provider.calls == 0 and visual["status"] == "NOT_REQUESTED"
        assert visual["frozen_composition_pack"] is None and _protected_counts(session) == baseline


def test_older_fourth_current_fact_is_visible_and_only_it_is_frozen(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        now = datetime.now(UTC)
        _fact(session, learning_session, key="activity:garden", category="ACTIVITY", statement="Gardens", observed_at=now)
        _fact(session, learning_session, key="pet:cat", category="PET", statement="Has a cat", observed_at=now)
        _fact(session, learning_session, key="preference:space", category="PREFERENCE", statement="Likes space", observed_at=now)
        _fact(session, learning_session, key="favorite:butterfly", category="FAVORITE", statement="Likes butterflies", observed_at=now.replace(year=now.year - 1))
        session.flush()
        catalogue, status = _catalogue(session, learning_session)
        assert status == "AVAILABLE" and len(catalogue) == 4
        assert {item["fact_key"] for item in catalogue} == {"activity:garden", "pet:cat", "preference:space", "favorite:butterfly"}
        baseline = _protected_counts(session)
        runtime, provider = _runtime(session, _order(personal_fact_keys=["favorite:butterfly"]), catalogue=catalogue)
        list(runtime.stream_turn(learning_session=learning_session, question="How does a butterfly grow?"))
        visual = _tutor_message(session, learning_session).payload["workspace_visual"]
        selected = visual["frozen_composition_pack"]["visual_learner_context"]["selected_personal_facts"]
        assert provider.calls == 1 and selected == [{"fact_key": "favorite:butterfly", "category": "FAVORITE", "display_statement": "Likes butterflies"}]
        assert _protected_counts(session) == baseline


def test_catalogue_allows_no_selection_and_is_all_or_nothing_on_overflow(factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        _fact(session, learning_session, key="favorite:butterfly", category="FAVORITE", statement="Likes butterflies", observed_at=datetime.now(UTC))
        session.flush()
        catalogue, status = _catalogue(session, learning_session)
        runtime, _ = _runtime(session, _order(personal_fact_keys=[]), catalogue=catalogue, catalogue_status=status)
        list(runtime.stream_turn(learning_session=learning_session, question="How does a butterfly grow?"))
        selected = _tutor_message(session, learning_session).payload["workspace_visual"]["frozen_composition_pack"]["visual_learner_context"]["selected_personal_facts"]
        assert selected == []

    with factory.begin() as session:
        learning_session = _learning_session(session)
        monkeypatch.setattr(tutor_context_module, "VISUAL_PERSONALIZATION_CATALOG_MAX_FACTS", 2)
        for index in range(3):
            _fact(session, learning_session, key=f"favorite:{index}", category="FAVORITE", statement=f"Likes {index}", observed_at=datetime.now(UTC))
        session.flush()
        catalogue, status = _catalogue(session, learning_session)
        assert catalogue == () and status == "CATALOG_CAPACITY_EXCEEDED"
        baseline = _protected_counts(session)
        runtime, provider = _runtime(session, _order(personal_fact_keys=[]), catalogue=catalogue, catalogue_status=status)
        list(runtime.stream_turn(learning_session=learning_session, question="How does a butterfly grow?"))
        message = _tutor_message(session, learning_session)
        assert provider.calls == 1 and message.payload["workspace_visual"]["status"] == "ADMITTED"
        assert message.payload["workspace_visual"]["frozen_composition_pack"]["visual_learner_context"]["selected_personal_facts"] == []
        assert message.payload["context_debug"]["visual_personalization_catalog_status"] == "CATALOG_CAPACITY_EXCEEDED"
        assert _protected_counts(session) == baseline


def test_catalogue_resolves_only_the_latest_value_per_fact_key(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        learning_session = _learning_session(session)
        now = datetime.now(UTC)
        like = _fact(session, learning_session, key="preference:animals", category="PREFERENCE", statement="LIKE", observed_at=now - timedelta(days=2))
        _fact(session, learning_session, key="preference:animals", category="PREFERENCE", statement="DISLIKE", observed_at=now - timedelta(days=1))
        session.flush()
        catalogue, status = _catalogue(session, learning_session)
        assert status == "AVAILABLE" and [item["display_statement"] for item in catalogue] == ["DISLIKE"]
        like.last_observed_at = now
        session.flush()
        catalogue, status = _catalogue(session, learning_session)
        assert status == "AVAILABLE" and [item["display_statement"] for item in catalogue] == ["LIKE"]
