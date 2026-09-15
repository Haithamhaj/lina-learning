"""Focused PostgreSQL acceptance contracts for canonical Concept continuity."""

from __future__ import annotations

import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from services.intelligence.concepts import (
    activate_registry,
    active_registry,
    persist_primary_concept,
    persist_related_concepts,
)
from services.intelligence.current_state import CURRENT_STATE_POLICY_VERSION
from services.intelligence.patterns import PATTERN_POLICY_VERSION
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute, StreamComplete
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import (
    CandidateEvent, CanonicalConceptRegistryRecord, CurrentLearningState,
    IntelligenceProcessingRun, LearnerPattern, LearningEvidence, LearningEvent,
    LearningMessage, LearningSegment, LearningSegmentConceptLink, LearningSession,
    ModelTask, PatternEvidence, Student, User,
)
from services.platform.safety import SafetyAction, SafetyDecision
from services.retrieval.service import RetrievedBlock
from services.tutor.context import LiveSubjectContext, LiveSubjectOrigin, TutorContextBuilder, unknown_live_subject
from services.tutor.runtime import TutorRuntime
from services.tutor.segments import latest_prior_segment_for_concept, latest_valid_structured_segment_state
from services.tutor.teaching_methods import TEACHING_METHOD_REGISTRY_VERSION


pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL is required")


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE users, canonical_concept_registries CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _registry(session: Session) -> None:
    session.add(CanonicalConceptRegistryRecord(version="concept-v1", is_active=True, payload={"concepts": [
        {"concept_key": "math.long_division", "broad_subject": "MATH", "display_name_en": "Long Division", "display_name_ar": "القسمة المطولة", "aliases": ["long division", "long-division", "القسمة المطولة"]},
        {"concept_key": "math.equivalent_fractions", "broad_subject": "MATH", "display_name_en": "Equivalent Fractions", "display_name_ar": "الكسور المتكافئة", "aliases": ["equivalent fractions", "fractions equal"]},
        {"concept_key": "science.water_cycle", "broad_subject": "SCIENCE", "display_name_en": "Water Cycle", "display_name_ar": "دورة الماء", "aliases": ["water cycle", "دورة الماء"]},
    ]}))
    session.flush()


def _student_session(session: Session, *, subject: str = "MATH") -> LearningSession:
    user = User(identity_provider="fixture", external_subject=uuid4().hex)
    session.add(user); session.flush()
    student = Student(user_id=user.id)
    session.add(student); session.flush()
    value = LearningSession(student_id=student.id, subject=subject, status="OPEN")
    session.add(value); session.flush()
    return value


def _segment(session: Session, learning_session: LearningSession, sequence: int) -> LearningSegment:
    value = LearningSegment(session_id=learning_session.id, sequence=sequence)
    session.add(value); session.flush()
    return value


def test_primary_identity_maps_aliases_and_unmapped_fails_open(factory: sessionmaker[Session]) -> None:
    """Catches persistence that invents a Concept or splits Arabic/English aliases."""
    with factory.begin() as session:
        _registry(session)
        learning_session = _student_session(session)
        english, arabic, unknown = (_segment(session, learning_session, item) for item in (1, 2, 3))
        persist_primary_concept(session, segment=english, subject="MATH", concept_ref="long-division", conversation_subject_hint="MATH")
        persist_primary_concept(session, segment=arabic, subject="MATH", concept_ref="القسمة المطولة", conversation_subject_hint="MATH")
        persist_primary_concept(session, segment=unknown, subject="MATH", concept_ref="not registered")

        assert (getattr(english, "conversation_subject_hint", None), english.primary_concept_ref, english.primary_concept_key, english.concept_registry_version, english.concept_mapping_status) == ("MATH", "long-division", "math.long_division", "concept-v1", "MAPPED")
        assert not hasattr(english, "broad_subject")
        assert arabic.primary_concept_key == english.primary_concept_key
        assert (unknown.primary_concept_key, unknown.concept_mapping_status) == (None, "UNMAPPED")
        assert session.scalars(select(LearningSegmentConceptLink).where(LearningSegmentConceptLink.segment_id == unknown.id)).all() == []


def test_continue_preserves_an_established_primary_concept_when_the_model_changes_topic(
    factory: sessionmaker[Session],
) -> None:
    """Catches a CONTINUE turn silently replacing an existing Segment identity."""

    with factory.begin() as session:
        _registry(session)
        learning_session = _student_session(session)
        segment = _segment(session, learning_session, 1)
        persist_primary_concept(
            session,
            segment=segment,
            subject="MATH",
            concept_ref="long division",
            conversation_subject_hint="MATH",
        )
        persist_primary_concept(
            session,
            segment=segment,
            subject="MATH",
            concept_ref="equivalent fractions",
            preserve_existing=True,
        )

        assert segment.primary_concept_key == "math.long_division"
        assert segment.primary_concept_ref == "long division"


def test_related_links_deduplicate_and_prior_selection_is_student_scoped(factory: sessionmaker[Session]) -> None:
    """Catches duplicate links or prior continuity crossing Segment/Student boundaries."""
    with factory.begin() as session:
        _registry(session)
        mine, other = _student_session(session), _student_session(session)
        old, newer, current = (_segment(session, mine, item) for item in (1, 2, 3))
        foreign = _segment(session, other, 1)
        for segment in (old, newer, current, foreign):
            persist_primary_concept(session, segment=segment, subject="MATH", concept_ref="long division")
        persist_related_concepts(session, segment=current, subject="SCIENCE", concept_refs=["water cycle", "water cycle", "not registered"])
        persist_related_concepts(session, segment=current, subject="MATH", concept_refs=["long division"])
        source = LearningMessage(session_id=mine.id, segment_id=newer.id, role="student", content="prior")
        session.add(source); session.flush()
        newer.structured_state = {"schema_version": "structured-segment-state-v1", "active_goal": "newest", "unresolved_point": None, "active_references": [], "established_facts": [], "source_message_ids": [str(source.id)]}
        selected = latest_prior_segment_for_concept(session, learning_session=mine, current_segment=current)

        assert selected is newer
        assert latest_valid_structured_segment_state(session, segment=selected).active_goal == "newest"  # type: ignore[union-attr]
        links = session.scalars(select(LearningSegmentConceptLink).where(LearningSegmentConceptLink.segment_id == current.id)).all()
        assert {row.concept_key for row in links} == {"science.water_cycle"}

        related_target = _segment(session, mine, 4)
        persist_primary_concept(session, segment=related_target, subject="SCIENCE", concept_ref="water cycle")
        assert latest_prior_segment_for_concept(session, learning_session=mine, current_segment=related_target) is None


def test_registry_database_allows_at_most_one_active_row(factory: sessionmaker[Session]) -> None:
    """Catches a nondeterministic reference mapping caused by two active registries."""

    with pytest.raises(IntegrityError):
        with factory.begin() as session:
            _registry(session)
            session.add(CanonicalConceptRegistryRecord(version="concept-v2", is_active=True, payload={"concepts": []}))
            session.flush()


def test_zero_active_registry_fails_open(factory: sessionmaker[Session]) -> None:
    """Catches runtime selection inventing a canonical mapping without active reference data."""

    with factory.begin() as session:
        session.add(CanonicalConceptRegistryRecord(version="concept-v1", is_active=False, payload={"concepts": []}))
        session.flush()
        assert active_registry(session) is None


def test_registry_activation_switches_the_only_active_row_without_rewriting_history(
    factory: sessionmaker[Session],
) -> None:
    """Catches a registry swap that leaves two active rows or mutates learner data."""

    with factory.begin() as session:
        _registry(session)
        learning_session = _student_session(session)
        segment = _segment(session, learning_session, 1)
        persist_primary_concept(session, segment=segment, subject="MATH", concept_ref="long division")
        before = (segment.primary_concept_key, segment.concept_registry_version)
        replacement = CanonicalConceptRegistryRecord(
            version="concept-v2", is_active=False, payload={"concepts": []},
        )
        session.add(replacement)
        session.flush()

        activate_registry(session, registry_id=replacement.id)

        active = session.scalars(
            select(CanonicalConceptRegistryRecord).where(CanonicalConceptRegistryRecord.is_active.is_(True))
        ).all()
        assert [row.version for row in active] == ["concept-v2"]
        assert (segment.primary_concept_key, segment.concept_registry_version) == before


def test_conversation_hint_never_reroutes_unknown_turn_retrieval_or_ordinary_li(
    factory: sessionmaker[Session],
) -> None:
    """Catches a model hint becoming an ordinary runtime Subject authority."""

    retrieval = _Retrieval()
    with factory.begin() as session:
        _registry(session)
        learning_session = _student_session(session)
        segment = _segment(session, learning_session, 1)
        persist_primary_concept(session, segment=segment, subject="MATH", concept_ref="equivalent fractions", conversation_subject_hint="MATH")
        context = TutorContextBuilder(session, retrieval_service=retrieval).build(
            learning_session=learning_session,
            question="Continue equivalent fractions.",
            live_subject_context=unknown_live_subject(),
        )

    assert context.subject is None
    assert context.retrieval == ()
    assert context.intelligence == ()


def test_unknown_live_subject_uses_hint_for_conditional_history_only(
    factory: sessionmaker[Session],
) -> None:
    """Catches either losing safe continuity or promoting a model hint into ordinary LI."""

    with factory.begin() as session:
        _registry(session)
        learning_session = _student_session(session)
        student = session.get(Student, learning_session.student_id)
        assert student is not None
        run = IntelligenceProcessingRun(student_id=student.id, rubric_version="fixture", policy_version="fixture", scope={})
        session.add(run); session.flush()
        segment = _segment(session, learning_session, 1)
        persist_primary_concept(
            session,
            segment=segment,
            subject="MATH",
            concept_ref="equivalent fractions",
            conversation_subject_hint="MATH",
        )
        session.add(CurrentLearningState(
            student_id=student.id,
            processing_run_id=run.id,
            subject="MATH",
            state_type="support_need",
            concept_ref="equivalent fractions",
            detail="Hint-scoped conditional history",
            policy_version=CURRENT_STATE_POLICY_VERSION,
        ))
        context = TutorContextBuilder(session, retrieval_service=_Retrieval()).build(
            learning_session=learning_session,
            question="Continue equivalent fractions.",
            live_subject_context=unknown_live_subject(),
        )

    assert context.subject is None
    assert context.retrieval == ()
    assert context.intelligence == ()
    assert context.prior_concept_context is not None
    assert "Hint-scoped conditional history" in context.prior_concept_context


def test_trusted_live_subject_outranks_conflicting_conversation_hint(
    factory: sessionmaker[Session],
) -> None:
    """Catches persisted model topic metadata overriding trusted server/Studio scope."""

    with factory.begin() as session:
        _registry(session)
        learning_session = _student_session(session)
        segment = _segment(session, learning_session, 1)
        persist_primary_concept(session, segment=segment, subject="MATH", concept_ref="equivalent fractions", conversation_subject_hint="MATH")
        context = TutorContextBuilder(session, retrieval_service=_Retrieval()).build(
            learning_session=learning_session,
            question="Explain evaporation.",
            live_subject_context=LiveSubjectContext("SCIENCE", LiveSubjectOrigin.CANVAS_SCENE),
        )

    assert context.subject == "SCIENCE"


class _Retrieval:
    def retrieve(self, **_: object) -> list[RetrievedBlock]:
        return []


class _Policy:
    def evaluate(self, **_: object) -> SafetyDecision:
        return SafetyDecision(SafetyAction.ALLOW, None, "BASELINE", 1, "TEST_ALLOW", "normal", None)


class _Provider:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def stream(self, route: ModelRoute, payload: dict[str, object]):
        del route
        self.payloads.append(payload)
        yield StreamComplete(ModelResult(output={
            "text": "Let's continue.", "suggested_actions": [], "guided_check": None,
            "teaching_mode": None, "teaching_strategy": None,
            "teaching_method_id": None, "prior_method_relation": None,
            "segment_relation": "CONTINUE", "structured_segment_state": None,
            "parent_boundary": None, "candidate_metadata": None,
            "provisional_broad_subject": None, "segment_concept_ref": None,
            "workspace_intent": None, "canvas_brief": None,
            "canvas_visual_context_selection": None, "workspace_visual_order": None,
        }))


def _scope(*, subject: str, concept_ref: str) -> dict[str, str]:
    return {"scope_type": "concept", "subject": subject, "concept_ref": concept_ref}


def _seed_pattern_lineage(
    session: Session, *, student: Student, learning_session: LearningSession, run: IntelligenceProcessingRun,
    pattern_type: str, pattern_key: str, candidate_payload: dict[str, object], detail: str,
) -> LearnerPattern:
    source = LearningMessage(session_id=learning_session.id, role="student", content="source reasoning")
    candidate = CandidateEvent(session_id=learning_session.id, message_id=None, event_type="strategy_outcome", concept_ref="equivalent fractions", signal=pattern_key, payload=candidate_payload)
    session.add_all((source, candidate)); session.flush()
    event = LearningEvent(processing_run_id=run.id, session_id=learning_session.id, candidate_event_id=candidate.id, subject="MATH", concept_ref="equivalent fractions", event_type="strategy_outcome", description="validated historical learning", source_message_id=source.id)
    session.add(event); session.flush()
    evidence = LearningEvidence(event_id=event.id, concept_ref="equivalent fractions", dimensions={}, relationship="supports", source_ref="segment-review")
    pattern = LearnerPattern(student_id=student.id, processing_run_id=run.id, pattern_type=pattern_type, pattern_key=pattern_key, scope=_scope(subject="MATH", concept_ref="equivalent fractions"), scope_key=json.dumps(_scope(subject="MATH", concept_ref="equivalent fractions"), sort_keys=True, separators=(",", ":")), policy_version=PATTERN_POLICY_VERSION, status="ACTIVE", support_count=2, detail=detail)
    session.add_all((evidence, pattern)); session.flush()
    session.add(PatternEvidence(pattern_id=pattern.id, evidence_id=evidence.id, relationship="supports", processing_run_id=run.id, policy_version=PATTERN_POLICY_VERSION, task_ref="fixture", context_ref="fixture", cycle_number=1))
    session.flush()
    return pattern


def test_actual_primary_tutor_payload_keeps_validated_strategy_and_misconception_history_conditional(
    factory: sessionmaker[Session],
) -> None:
    """Acceptance A/B: real DB lineage reaches only the actual primary payload's conditional section."""

    with factory.begin() as session:
        _registry(session)
        learning_session = _student_session(session)
        student = session.get(Student, learning_session.student_id)
        assert student is not None
        run = IntelligenceProcessingRun(student_id=student.id, rubric_version="fixture", policy_version="fixture", scope={})
        session.add(run); session.flush()
        current = _segment(session, learning_session, 1)
        persist_primary_concept(session, segment=current, subject="MATH", concept_ref="equivalent fractions")
        session.add(CurrentLearningState(student_id=student.id, processing_run_id=run.id, subject="MATH", state_type="support_need", concept_ref="equivalent fractions", detail="Compare the same-sized whole before matching fractions.", policy_version=CURRENT_STATE_POLICY_VERSION))
        _seed_pattern_lineage(session, student=student, learning_session=learning_session, run=run, pattern_type="strategy_effectiveness", pattern_key="strategy:visual_representation", candidate_payload={"strategy_key": "VISUAL_REPRESENTATION", "strategy_registry_version": TEACHING_METHOD_REGISTRY_VERSION, "observed_student_outcome": "enabled_independent_success"}, detail="Validated visual representation outcome.")
        _seed_pattern_lineage(session, student=student, learning_session=learning_session, run=run, pattern_type="misconception_recurrence", pattern_key="misconception:parts", candidate_payload={"misconception_evidence": {"incorrect_model": "Changing numerator and denominator independently keeps the fraction equal."}}, detail="Validated misconception recurrence.")
        provider = _Provider()
        runtime = TutorRuntime(session, context_builder=TutorContextBuilder(session, retrieval_service=_Retrieval()), safety_policy=_Policy(), gateway=ModelGateway(session, routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")}, providers={"fixture": provider}))
        list(runtime.stream_turn(learning_session=learning_session, question="Continue equivalent fractions."))

    assert len(provider.payloads) == 1
    actual = str(provider.payloads[0]["input"])
    conditional = actual.split("Conditional prior Concept context", 1)[1]
    ordinary = actual.split("Conditional prior Concept context", 1)[0]
    assert "math.equivalent_fractions" in conditional
    assert "VISUAL_REPRESENTATION" in conditional
    assert "enabled_independent_success" in conditional
    assert "Changing numerator and denominator independently keeps the fraction equal." in conditional
    assert "advisory; current Student behavior wins" in conditional
    assert "Ignore it completely if segment_relation is NEW_SEGMENT or UNCERTAIN" in conditional
    assert "VISUAL_REPRESENTATION" not in ordinary
    assert "Changing numerator and denominator independently keeps the fraction equal." not in ordinary


def test_canonical_concept_history_is_database_scoped_to_the_current_student(
    factory: sessionmaker[Session],
) -> None:
    """Acceptance C: same Concept never grants another Student's segment, State, or Pattern."""

    with factory.begin() as session:
        _registry(session)
        mine, other = _student_session(session), _student_session(session)
        mine_student = session.get(Student, mine.student_id)
        other_student = session.get(Student, other.student_id)
        assert mine_student is not None and other_student is not None
        mine_current, other_prior = _segment(session, mine, 1), _segment(session, other, 1)
        persist_primary_concept(session, segment=mine_current, subject="MATH", concept_ref="equivalent fractions")
        persist_primary_concept(session, segment=other_prior, subject="MATH", concept_ref="equivalent fractions")
        source = LearningMessage(session_id=other.id, segment_id=other_prior.id, role="student", content="Other Student private orientation")
        session.add(source); session.flush()
        other_prior.structured_state = {"schema_version": "structured-segment-state-v1", "active_goal": "Other Student private goal", "unresolved_point": None, "active_references": [], "established_facts": [], "source_message_ids": [str(source.id)]}
        run = IntelligenceProcessingRun(student_id=other_student.id, rubric_version="fixture", policy_version="fixture", scope={})
        session.add(run); session.flush()
        session.add(CurrentLearningState(student_id=other_student.id, processing_run_id=run.id, subject="MATH", state_type="support_need", concept_ref="equivalent fractions", detail="Other Student private State", policy_version=CURRENT_STATE_POLICY_VERSION))
        _seed_pattern_lineage(session, student=other_student, learning_session=other, run=run, pattern_type="strategy_effectiveness", pattern_key="strategy:visual_representation", candidate_payload={"strategy_key": "VISUAL_REPRESENTATION", "strategy_registry_version": TEACHING_METHOD_REGISTRY_VERSION, "observed_student_outcome": "helped"}, detail="Other Student private Pattern")
        provider = _Provider()
        runtime = TutorRuntime(session, context_builder=TutorContextBuilder(session, retrieval_service=_Retrieval()), safety_policy=_Policy(), gateway=ModelGateway(session, routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")}, providers={"fixture": provider}))
        list(runtime.stream_turn(learning_session=mine, question="Continue equivalent fractions."))

    actual = str(provider.payloads[0]["input"])
    assert "Other Student private orientation" not in actual
    assert "Other Student private goal" not in actual
    assert "Other Student private State" not in actual
    assert "Other Student private Pattern" not in actual
    assert "Validated historical outcome: helped" not in actual


def test_canonical_context_selects_matching_rows_without_semantic_projection_or_embedding(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Acceptance E: deterministic canonical selection succeeds while semantic dependencies are forbidden."""

    import services.intelligence.card as card_module
    import services.tutor.context as context_module

    def forbidden(*_: object, **__: object) -> object:
        raise AssertionError("canonical Concept context must not use semantic projection or embeddings")

    monkeypatch.setattr(card_module, "_semantic_candidates", forbidden)
    monkeypatch.setattr(context_module, "has_eligible_semantic_projection", forbidden)
    with factory.begin() as session:
        _registry(session)
        learning_session = _student_session(session)
        student = session.get(Student, learning_session.student_id)
        assert student is not None
        run = IntelligenceProcessingRun(student_id=student.id, rubric_version="fixture", policy_version="fixture", scope={})
        session.add(run); session.flush()
        current = _segment(session, learning_session, 1)
        persist_primary_concept(session, segment=current, subject="MATH", concept_ref="equivalent fractions")
        session.add(CurrentLearningState(student_id=student.id, processing_run_id=run.id, subject="MATH", state_type="support_need", concept_ref="equivalent fractions", detail="Deterministically selected State", policy_version=CURRENT_STATE_POLICY_VERSION))
        context = TutorContextBuilder(session, retrieval_service=_Retrieval()).build(learning_session=learning_session, question="Continue equivalent fractions.")

    assert context.prior_concept_context is not None
    assert "math.equivalent_fractions" in context.prior_concept_context
    assert "Deterministically selected State" in context.prior_concept_context


def test_invalid_misconception_provenance_is_omitted_from_actual_tutor_payload(
    factory: sessionmaker[Session],
) -> None:
    """Acceptance B: a generic Pattern cannot be promoted into guessed misconception meaning."""

    with factory.begin() as session:
        _registry(session)
        learning_session = _student_session(session)
        student = session.get(Student, learning_session.student_id)
        assert student is not None
        run = IntelligenceProcessingRun(student_id=student.id, rubric_version="fixture", policy_version="fixture", scope={})
        session.add(run); session.flush()
        current = _segment(session, learning_session, 1)
        persist_primary_concept(session, segment=current, subject="MATH", concept_ref="equivalent fractions")
        _seed_pattern_lineage(session, student=student, learning_session=learning_session, run=run, pattern_type="misconception_recurrence", pattern_key="misconception:missing-grounding", candidate_payload={}, detail="Generic recurrence without grounded misconception provenance.")
        provider = _Provider()
        runtime = TutorRuntime(session, context_builder=TutorContextBuilder(session, retrieval_service=_Retrieval()), safety_policy=_Policy(), gateway=ModelGateway(session, routes={ModelTask.TUTOR: ModelRoute("fixture", "fixture-tutor")}, providers={"fixture": provider}))
        list(runtime.stream_turn(learning_session=learning_session, question="Continue equivalent fractions."))

    actual = str(provider.payloads[0]["input"])
    assert "Historical misconception:" not in actual
    assert "Generic recurrence without grounded misconception provenance." not in actual
