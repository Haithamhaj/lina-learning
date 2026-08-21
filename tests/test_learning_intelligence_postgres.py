"""Phase 2–3 vertical-loop tests against PostgreSQL-derived records."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from services.content.indexing import build_content_index
from services.content.repository import (
    create_content_document,
    create_processing_run,
    create_semantic_items,
    create_semantic_processing_run,
    create_structural_items,
)
from services.content.semantic_contract import SemanticExtractionItem
from services.content.structural_contract import NormalizedStructuralItem
from services.intelligence.core import (
    close_and_consolidate,
    consolidate_student_history,
)
from services.platform.db.connection import normalize_database_url
from services.model_gateway.gateway import ModelGateway, ModelResult, ModelRoute
from services.platform.db.models import (
    CandidateEvent,
    CurrentLearningState,
    LearningEvidence,
    ModelTask,
    Student,
    User,
)
from services.tutor.runtime import start_session, tutor_turn
from services.tutor.session_lifecycle import (
    SessionLifecyclePolicy,
    close_inactive_sessions,
)


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL is required"
)


@pytest.fixture
def postgres_session_factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE learning_evidence, learning_events, candidate_events, learning_messages, learning_sessions, current_learning_states, pattern_evidence, learner_patterns, learner_intelligence_cards, decision_views, intelligence_processing_runs, indexed_content_block_sources, indexed_content_blocks, content_index_runs, content_semantic_item_sources, content_semantic_items, content_semantic_processing_runs, document_structural_items, content_blocks, curriculum_nodes, content_processing_runs, content_documents CASCADE"
            )
        )
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def test_tutor_runtime_uses_retrieval_without_creating_candidate_events(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    with postgres_session_factory.begin() as session:
        user = User(identity_provider="fixture", external_subject=uuid4().hex)
        session.add(user)
        session.flush()
        student = Student(user_id=user.id, display_name="Sandbox")
        session.add(student)
        session.flush()
        document = create_content_document(
            session,
            student_id=student.id,
            grade_level=5,
            subject="MATH",
            original_storage_key="fixture",
            original_checksum=uuid4().hex + uuid4().hex,
            filename="place-value.md",
            content_type="text/markdown",
        )
        run = create_processing_run(
            session,
            document_id=document.id,
            kind="STRUCTURAL",
            processor_version="fixture-v1",
        )
        run.status = "COMPLETED"
        structural = create_structural_items(
            session,
            document_id=document.id,
            processing_run_id=run.id,
            items=[
                NormalizedStructuralItem(
                    item_key="exercise",
                    parent_item_key=None,
                    sibling_order=0,
                    reading_order=0,
                    hierarchy_depth=0,
                    item_type="text",
                    text="Use place value to multiply decimal numbers by 10. 3.452 × 10 = 34.52.",
                    caption_text=None,
                    caption_item_keys=(),
                    heading_level=1,
                    page_number=2,
                    source_ref="fixture#page=2",
                    provenance={},
                    attributes={},
                )
            ],
        )
        semantic = create_semantic_processing_run(
            session,
            document_id=document.id,
            structural_processing_run_id=run.id,
            semantic_schema_version="fixture-v1",
            prompt_version="fixture-v1",
            model_route_version="fixture",
            provider="fixture",
            model="fixture",
            settings_version="fixture-v1",
            settings_metadata={},
        )
        semantic.status = "COMPLETED"
        create_semantic_items(
            session,
            document_id=document.id,
            semantic_processing_run_id=semantic.id,
            structural_items_by_key={"exercise": structural[0]},
            items=[
                SemanticExtractionItem(
                    semantic_key="place-value",
                    semantic_type="EXERCISE",
                    title="Multiply decimals by 10",
                    description=None,
                    normalized_concept_key="place-value",
                    parent_semantic_key=None,
                    structural_item_keys=["exercise"],
                    sibling_order=0,
                    metadata={},
                )
            ],
        )
        build_content_index(
            session,
            document=document,
            semantic_run=semantic,
            gateway=_embedding_gateway(session),
        )
        first = start_session(session, student_id=student.id)
        turn = tutor_turn(
            session, learning_session=first, question="Can we multiply 8.2 by 10?"
        )
        assert turn.sources[0]["source_ref"] == "fixture#page=2"
        assert session.query(CandidateEvent).count() == 0


def _embedding_gateway(session: Session) -> ModelGateway:
    class Provider:
        def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
            del route
            return ModelResult(
                output={"embeddings": [[0.01] * 1536 for _ in payload["input"]]}
            )

    return ModelGateway(
        session,
        routes={ModelTask.EMBEDDING: ModelRoute("fixture", "text-embedding-3-small")},
        providers={"fixture": Provider()},
    )


def test_inactive_session_closes_once_and_leaves_consolidation_for_later_task(
    postgres_session_factory: sessionmaker[Session],
) -> None:
    now = datetime(2026, 8, 21, 12, tzinfo=UTC)
    policy = SessionLifecyclePolicy(
        version="fixture-v1",
        inactivity=timedelta(minutes=10),
        grace=timedelta(minutes=5),
    )
    with postgres_session_factory.begin() as session:
        user = User(identity_provider="fixture", external_subject=uuid4().hex)
        session.add(user)
        session.flush()
        student = Student(user_id=user.id)
        session.add(student)
        session.flush()
        learning_session = start_session(session, student_id=student.id)
        learning_session.last_activity_at = now - timedelta(hours=1)
        assert close_inactive_sessions(session, now=now, policy=policy) == [
            learning_session
        ]
    with postgres_session_factory() as session:
        assert (
            session.get(type(learning_session), learning_session.id).status == "CLOSED"
        )
        assert close_inactive_sessions(session, now=now, policy=policy) == []
