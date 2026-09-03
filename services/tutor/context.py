"""Compact, inspectable inputs for a future Tutor runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from services.intelligence.card import CardBudget, build_learner_intelligence_card
from services.intelligence.selection import RelevantIntelligence
from services.model_gateway.factory import create_embedding_gateway
from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.personal_facts.memory_document import format_current_personal_memory_card
from services.platform.core_profile import StudentCoreContext, student_core_context
from services.platform.db.models import LearningExchangeEmbedding, LearningMessage, LearningSession, ModelTask
from services.retrieval.service import CurrentFocus, QueryEmbedding, RetrievedBlock, RetrievalService
from services.studio.tutor_context import StudioTutorWorkspaceContext
from services.tutor.exchanges import SEMANTIC_RECALL_MIN_COSINE_SIMILARITY, ConversationExchangeContext, complete_exchanges_for_segment, immediate_exchange_for_current_turn, persist_exchange_embedding, serialize_exchange
from services.tutor.segments import latest_segment_for_session, latest_valid_structured_segment_state


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContextBudget:
    max_question_characters: int = 4000
    retrieval_characters: int = 1400
    intelligence_characters: int = 600
    focus_message_count: int = 4
    recent_exchange_count: int = 1
    semantic_recall_exchange_count: int = 2
    embedding_batch_limit: int = 8


@dataclass(frozen=True)
class SessionContextMessage:
    message_id: UUID
    role: str
    content: str


@dataclass(frozen=True)
class TutorContextDebug:
    focus: CurrentFocus | None
    session_message_ids: tuple[UUID, ...]
    retrieval_source_refs: tuple[str, ...]
    intelligence_source_ids: tuple[UUID, ...]
    intelligence_source_kinds: tuple[str, ...]
    intelligence_card_schema_version: str = "not-built"
    intelligence_card_policy_version: str = "not-built"
    current_turn_message_id: UUID | None = None
    immediate_exchange_message_ids: tuple[UUID, ...] = ()
    older_continuity_message_ids: tuple[UUID, ...] = ()
    recent_exchange_message_ids: tuple[UUID, ...] = ()
    semantic_recall_exchange_message_ids: tuple[UUID, ...] = ()
    personal_memory_status: str = "PERSONAL_MEMORY_NOT_AVAILABLE"
    studio_runtime_id: UUID | None = None
    studio_snapshot_sequence: int | None = None
    studio_observation_id: UUID | None = None
    studio_from_sequence: int | None = None
    studio_through_sequence: int | None = None
    studio_selected_event_sequences: tuple[int, ...] = ()


@dataclass(frozen=True)
class TutorContext:
    question: str
    subject: str
    grade_level: int
    focus: CurrentFocus | None
    session_messages: tuple[SessionContextMessage, ...]
    retrieval: tuple[RetrievedBlock, ...]
    intelligence: tuple[RelevantIntelligence, ...]
    debug: TutorContextDebug
    student_core_context: StudentCoreContext = StudentCoreContext(None, None, None)
    personal_memory: str | None = None
    immediate_exchange: ConversationExchangeContext | None = None
    recent_exchanges: tuple[ConversationExchangeContext, ...] = ()
    semantic_recall_exchanges: tuple[ConversationExchangeContext, ...] = ()
    semantic_recall_priority_message_ids: tuple[tuple[UUID, ...], ...] = ()
    studio_workspace: StudioTutorWorkspaceContext | None = None

    @property
    def character_count(self) -> int:
        return (
            len(self.question)
            + _exchange_characters(self.immediate_exchange)
            + sum(_exchange_characters(exchange) for exchange in self.recent_exchanges)
            + sum(_exchange_characters(exchange) for exchange in self.semantic_recall_exchanges)
            + sum(len(message.content) for message in self.session_messages)
            + sum(len(block.text) for block in self.retrieval)
            + sum(len(item.text) for item in self.intelligence)
            + len(self.personal_memory or "")
            + (0 if self.studio_workspace is None else len(str(self.studio_workspace.as_model_payload())))
        )


class TutorContextBuilder:
    """Assemble deterministic context; it does not invoke a Tutor model."""

    def __init__(
        self,
        session: Session,
        *,
        retrieval_service: RetrievalService | None = None,
        budget: ContextBudget = ContextBudget(),
    ) -> None:
        self._session = session
        self._embedding_gateway: ModelGateway | None = None
        if retrieval_service is None:
            self._embedding_gateway = create_embedding_gateway(session)
            self._retrieval = RetrievalService(session, embedding_gateway=self._embedding_gateway)
        else:
            self._retrieval = retrieval_service
            gateway = getattr(retrieval_service, "_embedding_gateway", None)
            self._embedding_gateway = gateway if isinstance(gateway, ModelGateway) else None
        self._budget = budget

    def build(
        self,
        *,
        learning_session: LearningSession,
        question: str,
        current_turn_message_id: UUID | None = None,
        grade_level: int = 5,
        focus: CurrentFocus | None = None,
        studio_context: StudioTutorWorkspaceContext | None = None,
    ) -> TutorContext:
        question = question.strip()
        if not question:
            raise ValueError("A current Student question is required.")
        if len(question) > self._budget.max_question_characters:
            raise ValueError("Current Student question exceeds the context limit.")
        effective_focus = focus or self._session_focus(learning_session.id)
        current_turn = self._current_turn(
            learning_session=learning_session,
            current_turn_message_id=current_turn_message_id,
        )
        segment = latest_segment_for_session(self._session, session_id=learning_session.id)
        exchanges = (
            complete_exchanges_for_segment(
                self._session, learning_session=learning_session, segment=segment
            )
            if segment is not None
            else ()
        )
        immediate_exchange = immediate_exchange_for_current_turn(
            self._session,
            learning_session=learning_session,
            current_turn=current_turn,
        )
        immediate_ids = set(immediate_exchange.message_ids) if immediate_exchange is not None else set()
        remaining = tuple(
            exchange for exchange in exchanges
            if not set(exchange.message_ids).intersection(immediate_ids)
        )
        recent_exchanges = tuple(remaining[-self._budget.recent_exchange_count :])
        recent_ids = {message_id for exchange in recent_exchanges for message_id in exchange.message_ids}
        older = tuple(
            exchange for exchange in remaining
            if not set(exchange.message_ids).intersection(immediate_ids | recent_ids)
        )
        latest_state = latest_valid_structured_segment_state(self._session, segment=segment)
        semantic_recall, semantic_recall_priority, shared_query = self._semantic_recall(
            learning_session=learning_session,
            current_turn=current_turn,
            segment_id=segment.id if segment is not None else None,
            candidates=older,
            state_source_ids=set(latest_state.source_message_ids) if latest_state is not None else set(),
            question=question,
        )
        core_context = student_core_context(
            self._session,
            student_id=learning_session.student_id,
            as_of=date.today(),
        )
        retrieval_kwargs: dict[str, object] = {
            "student_id": learning_session.student_id,
            "question": question,
            "grade_level": core_context.grade_level if core_context.grade_level is not None else grade_level,
            "subject": learning_session.subject,
            "focus": effective_focus,
            "character_budget": self._budget.retrieval_characters,
        }
        if not shared_query.allows_generation:
            retrieval_kwargs["query_embedding"] = shared_query
        retrieval = tuple(self._retrieval.retrieve(**retrieval_kwargs))
        card = build_learner_intelligence_card(
            self._session,
            student_id=learning_session.student_id,
            subject=learning_session.subject,
            question=question,
            focus=effective_focus,
            budget=self._card_budget(),
        )
        intelligence = tuple(
            RelevantIntelligence(
                source_kind=entry.source_kind,
                source_id=entry.source_id,
                text=entry.text,
                concept_ref=entry.concept_ref,
                priority=entry.priority,
            )
            for entry in card.entries
        )
        personal_memory, personal_memory_status = self._personal_memory(
            learning_session=learning_session,
        )
        return TutorContext(
            question=question,
            subject=learning_session.subject,
            grade_level=grade_level,
            focus=effective_focus,
            immediate_exchange=immediate_exchange,
            recent_exchanges=recent_exchanges,
            semantic_recall_exchanges=semantic_recall,
            semantic_recall_priority_message_ids=tuple(
                exchange.message_ids for exchange in semantic_recall_priority
            ),
            session_messages=(),
            retrieval=retrieval,
            intelligence=intelligence,
            student_core_context=core_context,
            personal_memory=personal_memory,
            studio_workspace=studio_context,
            debug=TutorContextDebug(
                focus=effective_focus,
                session_message_ids=(),
                retrieval_source_refs=tuple(block.source_ref for block in retrieval),
                intelligence_source_ids=tuple(item.source_id for item in intelligence),
                intelligence_source_kinds=tuple(item.source_kind for item in intelligence),
                intelligence_card_schema_version=card.schema_version,
                intelligence_card_policy_version=card.policy_version,
                current_turn_message_id=current_turn.id if current_turn is not None else None,
                immediate_exchange_message_ids=immediate_exchange.message_ids if immediate_exchange is not None else (),
                older_continuity_message_ids=tuple(message_id for exchange in (*recent_exchanges, *semantic_recall) for message_id in exchange.message_ids),
                recent_exchange_message_ids=tuple(message_id for exchange in recent_exchanges for message_id in exchange.message_ids),
                semantic_recall_exchange_message_ids=tuple(message_id for exchange in semantic_recall for message_id in exchange.message_ids),
                personal_memory_status=personal_memory_status,
                studio_runtime_id=None if studio_context is None else studio_context.runtime_id,
                studio_snapshot_sequence=None if studio_context is None else studio_context.snapshot_sequence,
                studio_observation_id=None if studio_context is None else studio_context.observation_id,
                studio_from_sequence=(
                    None
                    if studio_context is None or not studio_context.unseen_events
                    else studio_context.unseen_events[0].sequence
                ),
                studio_through_sequence=None if studio_context is None else studio_context.through_sequence,
                studio_selected_event_sequences=(
                    () if studio_context is None else tuple(event.sequence for event in studio_context.unseen_events)
                ),
            ),
        )

    def _personal_memory(
        self,
        *,
        learning_session: LearningSession,
    ) -> tuple[str | None, str]:
        """Fail open only for an operational read failure in optional PF context."""

        try:
            with self._session.begin_nested():
                card = format_current_personal_memory_card(
                    self._session,
                    student_id=learning_session.student_id,
                )
        except OperationalError:
            logger.warning(
                "Personal Memory was omitted after an operational read failure.",
                extra={
                    "personal_memory_status": "PERSONAL_MEMORY_OMITTED_ERROR",
                    "student_id": str(learning_session.student_id),
                    "learning_session_id": str(learning_session.id),
                },
            )
            return None, "PERSONAL_MEMORY_OMITTED_ERROR"
        return card, "PERSONAL_MEMORY_INCLUDED" if card else "PERSONAL_MEMORY_NOT_AVAILABLE"

    def _card_budget(self) -> CardBudget:
        """Keep the existing Tutor allocation while using the centralized Card policy."""

        return CardBudget(max_characters=self._budget.intelligence_characters)

    def _current_turn(
        self,
        *,
        learning_session: LearningSession,
        current_turn_message_id: UUID | None,
    ) -> LearningMessage | None:
        if current_turn_message_id is None:
            return None
        message = self._session.get(LearningMessage, current_turn_message_id)
        if (
            message is None
            or message.session_id != learning_session.id
            or message.role != "student"
        ):
            raise ValueError("Current Turn must be a persisted Student message in this LearningSession.")
        return message

    def _semantic_recall(
        self,
        *,
        learning_session: LearningSession,
        current_turn: LearningMessage | None,
        segment_id: UUID | None,
        candidates: tuple[ConversationExchangeContext, ...],
        state_source_ids: set[UUID],
        question: str,
    ) -> tuple[
        tuple[ConversationExchangeContext, ...],
        tuple[ConversationExchangeContext, ...],
        QueryEmbedding,
    ]:
        if segment_id is None or not candidates:
            return (), (), QueryEmbedding.not_supplied()
        pinned = tuple(exchange for exchange in candidates if set(exchange.message_ids).intersection(state_source_ids))
        if self._embedding_gateway is None:
            selected = pinned[: self._budget.semantic_recall_exchange_count]
            return selected, selected, QueryEmbedding.unavailable()
        route = self._embedding_gateway.route_for(ModelTask.EMBEDDING)
        candidate_by_student_id = {exchange.student_message_id: exchange for exchange in candidates}
        candidate_student_ids = list(candidate_by_student_id)
        rows = self._session.execute(
            select(LearningExchangeEmbedding).where(
                LearningExchangeEmbedding.session_id == learning_session.id,
                LearningExchangeEmbedding.segment_id == segment_id,
                LearningExchangeEmbedding.student_message_id.in_(candidate_student_ids),
                LearningExchangeEmbedding.embedding_model == route.model,
            )
        ).scalars()
        stored = {row.student_message_id: row for row in rows}
        missing = sorted(
            (exchange for exchange in candidates if exchange.student_message_id not in stored),
            key=lambda exchange: (
                0 if exchange in pinned else 1,
                exchange.tutor_created_at,
                str(exchange.tutor_message_id),
            ),
        )[: self._budget.embedding_batch_limit]
        try:
            result = self._embedding_gateway.execute(
                ModelTask.EMBEDDING,
                {"input": [question, *(serialize_exchange(exchange) for exchange in missing)], "dimensions": 1536},
                lineage=AIExecutionLineage(
                    operation="tutor_context_embeddings",
                    student_id=learning_session.student_id,
                    learning_session_id=learning_session.id,
                    source_message_id=current_turn.id if current_turn is not None else None,
                ),
            )
            vectors = result.output.get("embeddings")
            if not isinstance(vectors, list) or len(vectors) != len(missing) + 1:
                raise ValueError("Embedding batch result count is invalid.")
            query = QueryEmbedding.available(vectors[0])
            message_rows = {
                message.id: message
                for message in self._session.execute(
                    select(LearningMessage).where(LearningMessage.id.in_([message_id for exchange in missing for message_id in exchange.message_ids]))
                ).scalars()
            }
            for exchange, vector in zip(missing, vectors[1:], strict=True):
                row = persist_exchange_embedding(
                    self._session,
                    student_message=message_rows[exchange.student_message_id],
                    tutor_message=message_rows[exchange.tutor_message_id],
                    embedding=vector,
                    embedding_model=route.model,
                    ai_execution_id=result.execution_id,
                )
                stored[exchange.student_message_id] = row
        except Exception:
            selected = pinned[: self._budget.semantic_recall_exchange_count]
            return selected, selected, QueryEmbedding.unavailable()
        distance = LearningExchangeEmbedding.embedding.cosine_distance(query.vector).label("distance")
        ranked_rows = self._session.execute(
            select(LearningExchangeEmbedding.student_message_id, distance)
            .join(LearningMessage, LearningMessage.id == LearningExchangeEmbedding.tutor_message_id)
            .where(
                LearningExchangeEmbedding.session_id == learning_session.id,
                LearningExchangeEmbedding.segment_id == segment_id,
                LearningExchangeEmbedding.student_message_id.in_(candidate_student_ids),
                LearningExchangeEmbedding.embedding_model == route.model,
                distance <= 1.0 - SEMANTIC_RECALL_MIN_COSINE_SIMILARITY,
            )
            .order_by(distance, LearningMessage.created_at.desc(), LearningMessage.id.desc())
        ).all()
        pinned_ids = {exchange.student_message_id for exchange in pinned}
        semantic = [
            candidate_by_student_id[student_message_id]
            for student_message_id, _ in ranked_rows
            if student_message_id not in pinned_ids
        ]
        selected = [*sorted(pinned, key=lambda exchange: (exchange.tutor_created_at, str(exchange.tutor_message_id)), reverse=True), *semantic]
        priority = tuple(selected[: self._budget.semantic_recall_exchange_count])
        presentation = tuple(
            sorted(priority, key=lambda item: (item.student_created_at, str(item.student_message_id)))
        )
        return presentation, priority, query

    def _session_focus(self, session_id: UUID) -> CurrentFocus | None:
        """Use recent persisted topic metadata only as conversational continuity."""

        messages = self._session.execute(
            select(LearningMessage)
            .where(LearningMessage.session_id == session_id)
            .order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())
            .limit(self._budget.focus_message_count)
        ).scalars()
        for message in messages:
            payload = message.payload if isinstance(message.payload, dict) else {}
            values = {
                "unit_key": payload.get("unit_key"),
                "lesson_key": payload.get("lesson_key"),
                "concept_key": payload.get("concept_key") or payload.get("concept_ref"),
            }
            normalized = {
                key: value for key, value in values.items() if isinstance(value, str) and value
            }
            if normalized:
                return CurrentFocus(**normalized)
        return None


def _exchange_characters(exchange: ConversationExchangeContext | None) -> int:
    return 0 if exchange is None else len(exchange.student_content or "") + len(exchange.tutor_content)
