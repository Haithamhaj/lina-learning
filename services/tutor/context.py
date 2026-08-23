"""Compact, inspectable inputs for a future Tutor runtime."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.intelligence.card import CardBudget, build_learner_intelligence_card
from services.intelligence.selection import RelevantIntelligence
from services.model_gateway.factory import create_embedding_gateway
from services.platform.db.models import LearningMessage, LearningSession
from services.retrieval.service import CurrentFocus, RetrievedBlock, RetrievalService


@dataclass(frozen=True)
class ContextBudget:
    max_question_characters: int = 4000
    session_characters: int = 600
    retrieval_characters: int = 1400
    intelligence_characters: int = 600
    recent_message_count: int = 4


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

    @property
    def character_count(self) -> int:
        return (
            len(self.question)
            + sum(len(message.content) for message in self.session_messages)
            + sum(len(block.text) for block in self.retrieval)
            + sum(len(item.text) for item in self.intelligence)
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
        self._retrieval = retrieval_service or RetrievalService(
            session,
            embedding_gateway=create_embedding_gateway(session),
        )
        self._budget = budget

    def build(
        self,
        *,
        learning_session: LearningSession,
        question: str,
        grade_level: int = 5,
        focus: CurrentFocus | None = None,
    ) -> TutorContext:
        question = question.strip()
        if not question:
            raise ValueError("A current Student question is required.")
        if len(question) > self._budget.max_question_characters:
            raise ValueError("Current Student question exceeds the context limit.")
        effective_focus = focus or self._session_focus(learning_session.id)
        messages = self._recent_messages(learning_session.id)
        retrieval = tuple(
            self._retrieval.retrieve(
                student_id=learning_session.student_id,
                question=question,
                grade_level=grade_level,
                subject=learning_session.subject,
                focus=effective_focus,
                character_budget=self._budget.retrieval_characters,
            )
        )
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
        return TutorContext(
            question=question,
            subject=learning_session.subject,
            grade_level=grade_level,
            focus=effective_focus,
            session_messages=messages,
            retrieval=retrieval,
            intelligence=intelligence,
            debug=TutorContextDebug(
                focus=effective_focus,
                session_message_ids=tuple(message.message_id for message in messages),
                retrieval_source_refs=tuple(block.source_ref for block in retrieval),
                intelligence_source_ids=tuple(item.source_id for item in intelligence),
                intelligence_source_kinds=tuple(item.source_kind for item in intelligence),
                intelligence_card_schema_version=card.schema_version,
                intelligence_card_policy_version=card.policy_version,
            ),
        )

    def _card_budget(self) -> CardBudget:
        """Keep the existing Tutor allocation while using the centralized Card policy."""

        return CardBudget(max_characters=self._budget.intelligence_characters)

    def _recent_messages(self, session_id: UUID) -> tuple[SessionContextMessage, ...]:
        rows = list(
            self._session.execute(
                select(LearningMessage)
                .where(LearningMessage.session_id == session_id)
                .order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())
                .limit(self._budget.recent_message_count)
            ).scalars()
        )
        used = 0
        selected: list[SessionContextMessage] = []
        for message in rows:
            if used + len(message.content) > self._budget.session_characters:
                break
            selected.append(SessionContextMessage(message.id, message.role, message.content))
            used += len(message.content)
        return tuple(reversed(selected))

    def _session_focus(self, session_id: UUID) -> CurrentFocus | None:
        """Use recent persisted topic metadata only as conversational continuity."""

        messages = self._session.execute(
            select(LearningMessage)
            .where(LearningMessage.session_id == session_id)
            .order_by(LearningMessage.created_at.desc(), LearningMessage.id.desc())
            .limit(self._budget.recent_message_count)
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
