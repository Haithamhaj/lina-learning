"""Short, database-authoritative lifecycle transitions for Studio interactions."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from services.model_gateway.gateway import (
    AIExecutionLineage,
    ModelGateway,
    ModelResult,
    ModelStreamEvent,
    StreamComplete,
)
from services.platform.config import get_settings
from services.platform.db.models import (
    AIExecution,
    LearningMessage,
    LearningSession,
    ModelTask,
    StudioEvent,
    StudioRuntime,
    StudioScene,
    StudioSnapshot,
    StudioStudentInteraction,
    StudioTutorObservation,
)
from services.studio.subjects import production_subject_registry
from services.studio.subjects import PRODUCTION_CURRENT_PROFILE_VERSIONS
from services.studio.subjects.contracts import (
    InteractionPolicy,
    SemanticValidationPolicy,
    ValidationResult,
    ValidationStatus,
)
from services.studio.subjects.registry import SubjectCapabilityError, SubjectCapabilityRegistry
from services.studio.workspace_intent import WorkspaceIntentContractError, parse_workspace_intent
from services.studio.router import ActiveSceneCapability, WorkspaceAuthorityContext, WorkspaceDecisionStatus, WorkspaceExecutionDecision, route_workspace_intent
from services.tutor.candidate_events import TUTOR_OUTPUT_RESPONSE_SCHEMA
from services.tutor.candidate_events import (
    PersistedGuidedLearningCheck,
    SuggestedAction,
    normalize_guided_learning_check,
    normalize_suggested_actions,
)


MAX_INTERACTION_TUTOR_CONTEXT_BYTES = 32_768
STUDIO_INTERACTION_TUTOR_OPERATION = "studio_interaction_tutor_turn"


class StudioInteractionError(ValueError):
    """Base error for a rejected Studio StudentInteraction transition."""


class StudioInteractionAccessDenied(StudioInteractionError):
    """An interaction is absent from the authenticated Student/Runtime scope."""


class StudioInteractionStateError(StudioInteractionError):
    """An interaction cannot make the requested lifecycle transition."""


class StudioInteractionSourceError(StudioInteractionError):
    """A persisted interaction no longer has an exact supported source contract."""


class StudioInteractionTutorOutputError(StudioInteractionError):
    """The internal Tutor result is incompatible with the current Tutor contract."""


@dataclass(frozen=True)
class StudioInteractionTutorContext:
    """Bounded source and current-Workspace context for one Canvas Tutor attempt."""

    interaction_id: UUID
    runtime_id: UUID
    learning_session_id: UUID
    source: Mapping[str, object]
    workspace: Mapping[str, object]

    def as_model_payload(self) -> dict[str, object]:
        return {
            "schema_version": "studio-interaction-tutor-context-v1",
            "interaction_id": str(self.interaction_id),
            "runtime_id": str(self.runtime_id),
            "learning_session_id": str(self.learning_session_id),
            "source": dict(self.source),
            "workspace": dict(self.workspace),
        }


@dataclass(frozen=True)
class StudioInteractionTutorResult:
    """Internal, non-finalizing primary Tutor result for a claimed Canvas interaction."""

    context: StudioInteractionTutorContext
    result: ModelResult


@dataclass(frozen=True)
class StudioInteractionTutorAdmission:
    """One claimed Canvas interaction plus its independent Workspace selection."""

    context: StudioInteractionTutorContext
    observation_id: UUID | None
    workspace_context: object


@dataclass(frozen=True)
class StudioInteractionTutorTurn:
    """A persisted Canvas Tutor message awaiting the short SSE finalization."""

    message_id: UUID
    text: str
    suggested_actions: list[SuggestedAction]
    guided_check: PersistedGuidedLearningCheck | None
    ai_execution_id: UUID


class StudioInteractionService:
    """Own short row-locked transitions; never hold a lock during model work."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def claim_pending(
        self,
        *,
        student_id: UUID,
        runtime_id: UUID,
        interaction_id: UUID,
    ) -> StudioStudentInteraction:
        """Atomically change exactly one owned PENDING interaction to RUNNING."""

        interaction = self.session.execute(
            select(StudioStudentInteraction)
            .where(
                StudioStudentInteraction.id == interaction_id,
                StudioStudentInteraction.student_id == student_id,
                StudioStudentInteraction.studio_runtime_id == runtime_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if interaction is None:
            raise StudioInteractionAccessDenied("Studio interaction was not found.")
        if interaction.status != "PENDING":
            raise StudioInteractionStateError("Studio interaction is not pending.")
        interaction.status = "RUNNING"
        self.session.flush()
        return interaction

    def supersede_running_for_new_student_interaction(
        self,
        *,
        student_id: UUID,
        runtime_id: UUID,
    ) -> None:
        """End older running Canvas turns at a newer trigger's durable boundary."""

        interactions = self.session.execute(
            select(StudioStudentInteraction)
            .where(
                StudioStudentInteraction.student_id == student_id,
                StudioStudentInteraction.studio_runtime_id == runtime_id,
                StudioStudentInteraction.status == "RUNNING",
            )
            .with_for_update()
        ).scalars()
        for interaction in interactions:
            interaction.status = "SUPERSEDED"
        self.session.flush()

    def supersede_running_for_new_chat_student_input(
        self,
        *,
        student_id: UUID,
        learning_session_id: UUID,
    ) -> None:
        """A later real Chat Student input supersedes a running Canvas turn.

        Runtime is the ordering owner for Canvas state.  This short transition
        is intentionally called at durable Chat-input admission, never after a
        provider response, so a Canvas terminal cannot race past newer input.
        """

        runtime = self.session.execute(
            select(StudioRuntime)
            .where(
                StudioRuntime.student_id == student_id,
                StudioRuntime.learning_session_id == learning_session_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if runtime is None:
            return
        self.supersede_running_for_new_student_interaction(
            student_id=student_id,
            runtime_id=runtime.id,
        )

    def require_chat_terminal_current(
        self,
        *,
        student_id: UUID,
        learning_session_id: UUID,
        through_event_sequence: int,
    ) -> None:
        """Reject a Chat terminal when a newer Tutor-triggering Canvas input won."""

        runtime = self.session.execute(
            select(StudioRuntime)
            .where(
                StudioRuntime.student_id == student_id,
                StudioRuntime.learning_session_id == learning_session_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if runtime is None:
            return
        newer_trigger = self.session.execute(
            select(StudioStudentInteraction.id)
            .join(StudioEvent, StudioStudentInteraction.source_event_id == StudioEvent.id)
            .where(
                StudioStudentInteraction.studio_runtime_id == runtime.id,
                StudioStudentInteraction.student_id == student_id,
                StudioEvent.sequence > through_event_sequence,
            )
            .limit(1)
        ).scalar_one_or_none()
        if newer_trigger is not None:
            raise StudioInteractionStateError("A newer Canvas Student interaction superseded this Chat Tutor result.")


class StudioInteractionTutorService:
    """Claim and execute one Canvas interaction without entering the Chat persistence path."""

    def __init__(
        self,
        *,
        bind: Engine | Connection,
        gateway_factory: Callable[[Session], ModelGateway],
        subject_registry: SubjectCapabilityRegistry | None = None,
    ) -> None:
        self._bind = bind
        self._gateway_factory = gateway_factory
        self._subject_registry = subject_registry or production_subject_registry()

    def admit(
        self,
        *,
        student_id: UUID,
        learning_session_id: UUID,
        runtime_id: UUID,
        interaction_id: UUID,
    ) -> StudioInteractionTutorAdmission:
        """Claim one exact interaction before a long-lived response body begins.

        The source context is immutable and independently authoritative.  The
        Workspace observation is deliberately selected only after the short
        claim transaction has committed, so neither lock is held during model
        transport.
        """

        context = self._claim_and_resolve(
            student_id=student_id,
            learning_session_id=learning_session_id,
            runtime_id=runtime_id,
            interaction_id=interaction_id,
        )
        # Import lazily: State persistence imports this module for its short
        # interaction transitions, while ordinary Tutor selection imports the
        # State service.  The admission boundary itself must not create a
        # package-import cycle.
        from services.studio.tutor_context import select_studio_tutor_context

        selection = select_studio_tutor_context(
            bind=self._bind,
            student_id=student_id,
            learning_session_id=learning_session_id,
            student_interaction_id=interaction_id,
        )
        if selection is None or selection.context.runtime_id != runtime_id:
            raise StudioInteractionSourceError("Studio interaction Runtime is unavailable for Workspace selection.")
        return StudioInteractionTutorAdmission(
            context=context,
            observation_id=selection.context.observation_id,
            workspace_context=selection.context,
        )

    def stream_admitted(
        self,
        *,
        admission: StudioInteractionTutorAdmission,
        student_id: UUID,
    ) -> Iterator[ModelStreamEvent]:
        """Run exactly one real Gateway stream for an already-admitted turn."""

        context = admission.context
        with Session(self._bind) as generation_session:
            gateway = self._gateway_factory(generation_session)
            try:
                for event in gateway.stream(
                    ModelTask.TUTOR,
                    self._model_payload(context, workspace_context=admission.workspace_context),
                    lineage=AIExecutionLineage(
                        operation=STUDIO_INTERACTION_TUTOR_OPERATION,
                        operation_id=context.interaction_id,
                        student_id=student_id,
                        learning_session_id=context.learning_session_id,
                        source_message_id=None,
                    ),
                ):
                    if isinstance(event, StreamComplete):
                        self._validate_tutor_output(event.result)
                    yield event
                generation_session.commit()
            except Exception:
                # Gateway writes its truthful completed/failed ledger entry in
                # this session.  Keep it even when the result is unusable.
                generation_session.commit()
                raise

    def persist_canvas_turn(
        self,
        *,
        admission: StudioInteractionTutorAdmission,
        result: ModelResult,
        student_id: UUID,
        parent_boundary: Mapping[str, object] | None = None,
        override_text: str | None = None,
    ) -> StudioInteractionTutorTurn:
        """Persist one real Tutor message without entering the Chat write path.

        This is the Canvas terminal acceptance point: runtime then interaction
        are locked, causal supersession is rechecked, and the message is
        committed with exact gateway/source provenance in one short database
        transaction.  Completion remains separate until the server resumes
        after emitting the terminal SSE frame.
        """

        if result.execution_id is None:
            raise StudioInteractionTutorOutputError("Tutor Gateway did not return durable execution provenance.")
        context = admission.context
        with Session(self._bind) as persistence_session:
            with persistence_session.begin():
                # The shared causal order is LearningSession → StudioRuntime.
                # Chat input already owns this order; take the Session lock
                # before the Runtime so Canvas terminal persistence cannot form
                # a circular wait with a newer Chat admission.
                learning_session = persistence_session.execute(
                    select(LearningSession)
                    .where(
                        LearningSession.id == context.learning_session_id,
                        LearningSession.student_id == student_id,
                    )
                    .with_for_update()
                ).scalar_one_or_none()
                if learning_session is None:
                    raise StudioInteractionAccessDenied("Learning session was not found.")
                runtime = persistence_session.execute(
                    select(StudioRuntime)
                    .where(
                        StudioRuntime.id == context.runtime_id,
                        StudioRuntime.student_id == student_id,
                        StudioRuntime.learning_session_id == context.learning_session_id,
                    )
                    .with_for_update()
                ).scalar_one_or_none()
                if runtime is None:
                    raise StudioInteractionAccessDenied("Studio runtime was not found.")
                interaction = persistence_session.execute(
                    select(StudioStudentInteraction)
                    .where(
                        StudioStudentInteraction.id == context.interaction_id,
                        StudioStudentInteraction.studio_runtime_id == runtime.id,
                        StudioStudentInteraction.student_id == student_id,
                        StudioStudentInteraction.learning_session_id == context.learning_session_id,
                    )
                    .with_for_update()
                ).scalar_one_or_none()
                if interaction is None:
                    raise StudioInteractionAccessDenied("Studio interaction was not found.")
                if interaction.status != "RUNNING":
                    raise StudioInteractionStateError("Studio interaction is no longer current for Tutor persistence.")
                self._verify_execution_provenance_in_session(
                    persistence_session,
                    execution_id=result.execution_id,
                    interaction_id=interaction.id,
                    student_id=student_id,
                    learning_session_id=context.learning_session_id,
                )
                source_event_id = interaction.source_event_id
                text = override_text if override_text is not None else result.output.get("text")
                if not isinstance(text, str) or not text.strip():
                    raise StudioInteractionTutorOutputError("Tutor result lacks terminal response text.")
                proposed_guided_check = normalize_guided_learning_check(result.output.get("guided_check"))
                guided_check = (
                    PersistedGuidedLearningCheck(id=uuid4(), **proposed_guided_check.model_dump())
                    if proposed_guided_check is not None and override_text is None
                    else None
                )
                suggested_actions = [] if override_text is not None else normalize_suggested_actions(result.output.get("suggested_actions"))
                message = LearningMessage(
                    session_id=context.learning_session_id,
                    role="tutor",
                    content=text.strip(),
                    ai_execution_id=result.execution_id,
                    payload={
                        "tutor_turn_schema_version": "tutor_turn_v9",
                        "turn_origin": "STUDIO_INTERACTION",
                        "student_interaction_id": str(interaction.id),
                        "source_studio_event_id": str(source_event_id),
                        "ai_execution_id": str(result.execution_id),
                        "suggested_actions": [action.model_dump() for action in suggested_actions],
                        "guided_check": None if guided_check is None else guided_check.model_dump(mode="json"),
                        "workspace": self._workspace_audit(
                            result.output.get("workspace_intent"), admission.workspace_context
                        ),
                        "parent_boundary": None if parent_boundary is None else dict(parent_boundary),
                        "candidate_metadata_status": "not_applicable_canvas_interaction",
                    },
                    created_at=datetime.now(UTC),
                )
                persistence_session.add(message)
                learning_session.last_activity_at = datetime.now(UTC)
                persistence_session.flush()
                return StudioInteractionTutorTurn(
                    message_id=message.id,
                    text=message.content,
                    suggested_actions=suggested_actions,
                    guided_check=guided_check,
                    ai_execution_id=result.execution_id,
                )

    def finalize_delivered_turn(
        self,
        *,
        admission: StudioInteractionTutorAdmission,
        turn: StudioInteractionTutorTurn,
        student_id: UUID,
    ) -> None:
        """Mark only a server-terminal-delivered Canvas message complete."""

        context = admission.context
        with Session(self._bind) as finalization_session:
            with finalization_session.begin():
                runtime = finalization_session.execute(
                    select(StudioRuntime)
                    .where(StudioRuntime.id == context.runtime_id, StudioRuntime.student_id == student_id)
                    .with_for_update()
                ).scalar_one_or_none()
                if runtime is None:
                    raise StudioInteractionAccessDenied("Studio runtime was not found.")
                interaction = finalization_session.execute(
                    select(StudioStudentInteraction)
                    .where(
                        StudioStudentInteraction.id == context.interaction_id,
                        StudioStudentInteraction.studio_runtime_id == runtime.id,
                        StudioStudentInteraction.student_id == student_id,
                    )
                    .with_for_update()
                ).scalar_one_or_none()
                if interaction is None or interaction.status != "RUNNING":
                    raise StudioInteractionStateError("Studio interaction is no longer current for finalization.")
                self._verify_execution_provenance_in_session(
                    finalization_session,
                    execution_id=turn.ai_execution_id,
                    interaction_id=interaction.id,
                    student_id=student_id,
                    learning_session_id=context.learning_session_id,
                )
                message = finalization_session.get(LearningMessage, turn.message_id)
                if (
                    message is None
                    or message.session_id != context.learning_session_id
                    or message.role != "tutor"
                    or message.ai_execution_id != turn.ai_execution_id
                    or not isinstance(message.payload, dict)
                    or message.payload.get("turn_origin") != "STUDIO_INTERACTION"
                    or message.payload.get("student_interaction_id") != str(interaction.id)
                    or message.payload.get("source_studio_event_id") != str(interaction.source_event_id)
                ):
                    raise StudioInteractionTutorOutputError("Canvas Tutor message provenance is incomplete or inconsistent.")
                if admission.observation_id is not None:
                    observation = finalization_session.execute(
                        select(StudioTutorObservation)
                        .where(
                            StudioTutorObservation.id == admission.observation_id,
                            StudioTutorObservation.studio_runtime_id == runtime.id,
                            StudioTutorObservation.student_id == student_id,
                            StudioTutorObservation.student_interaction_id == interaction.id,
                        )
                        .with_for_update()
                    ).scalar_one_or_none()
                    if observation is None or observation.status != "SELECTED":
                        raise StudioInteractionStateError("Canvas Tutor observation is no longer selected.")
                    if observation.from_event_sequence != runtime.last_tutor_observation_sequence + 1:
                        raise StudioInteractionStateError("Canvas Tutor observation no longer begins at the watermark.")
                    if observation.through_event_sequence > runtime.latest_event_sequence:
                        raise StudioInteractionStateError("Canvas Tutor observation extends beyond Studio history.")
                    observation.status = "COMMITTED"
                    observation.ai_execution_id = turn.ai_execution_id
                    observation.completed_at = datetime.now(UTC)
                    runtime.last_tutor_observation_sequence = observation.through_event_sequence
                interaction.status = "COMPLETED"
                interaction.tutor_message_id = message.id
                interaction.ai_execution_id = turn.ai_execution_id
                interaction.completed_at = datetime.now(UTC)
                runtime.updated_at = datetime.now(UTC)
                finalization_session.flush()

    def abandon_admitted_turn(
        self,
        *,
        admission: StudioInteractionTutorAdmission,
        student_id: UUID,
        status: str,
    ) -> None:
        """Truthfully close an incomplete admitted turn without consuming Events."""

        if status not in {"FAILED", "CANCELLED"}:
            raise ValueError("Studio interaction terminal failure status is unsupported.")
        context = admission.context
        with Session(self._bind) as transition_session:
            with transition_session.begin():
                runtime = transition_session.execute(
                    select(StudioRuntime)
                    .where(StudioRuntime.id == context.runtime_id, StudioRuntime.student_id == student_id)
                    .with_for_update()
                ).scalar_one_or_none()
                if runtime is None:
                    return
                interaction = transition_session.execute(
                    select(StudioStudentInteraction)
                    .where(
                        StudioStudentInteraction.id == context.interaction_id,
                        StudioStudentInteraction.studio_runtime_id == runtime.id,
                        StudioStudentInteraction.student_id == student_id,
                    )
                    .with_for_update()
                ).scalar_one_or_none()
                if interaction is None or interaction.status != "RUNNING":
                    return
                interaction.status = status
                interaction.completed_at = datetime.now(UTC)
                if admission.observation_id is not None:
                    observation = transition_session.execute(
                        select(StudioTutorObservation)
                        .where(
                            StudioTutorObservation.id == admission.observation_id,
                            StudioTutorObservation.studio_runtime_id == runtime.id,
                            StudioTutorObservation.student_interaction_id == interaction.id,
                        )
                        .with_for_update()
                    ).scalar_one_or_none()
                    if observation is not None and observation.status == "SELECTED":
                        observation.status = "FAILED" if status == "FAILED" else "CANCELLED"
                        observation.completed_at = datetime.now(UTC)
                transition_session.flush()

    def execute(
        self,
        *,
        student_id: UUID,
        learning_session_id: UUID,
        runtime_id: UUID,
        interaction_id: UUID,
    ) -> StudioInteractionTutorResult:
        """Run exactly one claimed interaction through the existing Tutor Gateway task.

        The admission transaction commits before provider work begins.  The
        resulting interaction intentionally remains RUNNING: later Runtime-03
        work owns output delivery and terminal lifecycle transitions.
        """

        context = self._claim_and_resolve(
            student_id=student_id,
            learning_session_id=learning_session_id,
            runtime_id=runtime_id,
            interaction_id=interaction_id,
        )
        with Session(self._bind) as generation_session:
            gateway = self._gateway_factory(generation_session)
            try:
                result = gateway.execute(
                    ModelTask.TUTOR,
                    self._model_payload(context),
                    lineage=AIExecutionLineage(
                        operation=STUDIO_INTERACTION_TUTOR_OPERATION,
                        operation_id=interaction_id,
                        student_id=student_id,
                        learning_session_id=learning_session_id,
                        source_message_id=None,
                    ),
                )
                self._validate_tutor_output(result)
                generation_session.commit()
            except Exception:
                # ModelGateway has already recorded a truthful success/failure
                # attempt when it reached a provider.  Preserve that ledger row
                # while never finalizing this Canvas interaction here.
                generation_session.commit()
                raise
        self._verify_execution_provenance(
            execution_id=result.execution_id,
            interaction_id=interaction_id,
            student_id=student_id,
            learning_session_id=learning_session_id,
        )
        return StudioInteractionTutorResult(context=context, result=result)

    def _claim_and_resolve(
        self,
        *,
        student_id: UUID,
        learning_session_id: UUID,
        runtime_id: UUID,
        interaction_id: UUID,
    ) -> StudioInteractionTutorContext:
        """Resolve immutable sources then atomically admit one owned pending interaction."""

        with Session(self._bind) as admission_session:
            with admission_session.begin():
                runtime = admission_session.execute(
                    select(StudioRuntime)
                    .where(
                        StudioRuntime.id == runtime_id,
                        StudioRuntime.student_id == student_id,
                        StudioRuntime.learning_session_id == learning_session_id,
                    )
                    .with_for_update()
                ).scalar_one_or_none()
                if runtime is None:
                    raise StudioInteractionAccessDenied("Studio runtime was not found.")
                if runtime.status != "OPEN":
                    raise StudioInteractionStateError("Studio runtime is not open for Tutor execution.")
                learning_session = admission_session.execute(
                    select(LearningSession).where(
                        LearningSession.id == learning_session_id,
                        LearningSession.student_id == student_id,
                    )
                ).scalar_one_or_none()
                if learning_session is None:
                    raise StudioInteractionAccessDenied("Learning session was not found.")
                interaction = admission_session.execute(
                    select(StudioStudentInteraction).where(
                        StudioStudentInteraction.id == interaction_id,
                        StudioStudentInteraction.studio_runtime_id == runtime.id,
                        StudioStudentInteraction.student_id == student_id,
                        StudioStudentInteraction.learning_session_id == learning_session.id,
                    )
                ).scalar_one_or_none()
                if interaction is None:
                    raise StudioInteractionAccessDenied("Studio interaction was not found.")
                context = self._resolve_context(
                    admission_session=admission_session,
                    runtime=runtime,
                    interaction=interaction,
                )
                StudioInteractionService(admission_session).claim_pending(
                    student_id=student_id,
                    runtime_id=runtime.id,
                    interaction_id=interaction.id,
                )
                return context

    def _resolve_context(
        self,
        *,
        admission_session: Session,
        runtime: StudioRuntime,
        interaction: StudioStudentInteraction,
    ) -> StudioInteractionTutorContext:
        event = admission_session.execute(
            select(StudioEvent).where(
                StudioEvent.id == interaction.source_event_id,
                StudioEvent.studio_runtime_id == runtime.id,
                StudioEvent.student_id == runtime.student_id,
                StudioEvent.learning_session_id == runtime.learning_session_id,
            )
        ).scalar_one_or_none()
        if event is None or event.scene_id is None:
            raise StudioInteractionSourceError("Studio interaction source event is unavailable.")
        scene = admission_session.execute(
            select(StudioScene).where(
                StudioScene.id == event.scene_id,
                StudioScene.studio_runtime_id == runtime.id,
                StudioScene.student_id == runtime.student_id,
                StudioScene.learning_session_id == runtime.learning_session_id,
            )
        ).scalar_one_or_none()
        if scene is None:
            raise StudioInteractionSourceError("Studio interaction source Scene is unavailable.")
        snapshot = admission_session.execute(
            select(StudioSnapshot).where(
                StudioSnapshot.studio_runtime_id == runtime.id,
                StudioSnapshot.student_id == runtime.student_id,
            )
        ).scalar_one_or_none()
        if snapshot is None or snapshot.latest_event_sequence != runtime.latest_event_sequence:
            raise StudioInteractionSourceError("Studio interaction runtime Snapshot is inconsistent.")
        action_payload, validation = self._resolve_source_contract(event=event, scene=scene, interaction=interaction)
        return StudioInteractionTutorContext(
            interaction_id=interaction.id,
            runtime_id=runtime.id,
            learning_session_id=runtime.learning_session_id,
            source={
                "turn_origin": "CANVAS_INTERACTION",
                "interaction_kind": interaction.interaction_kind,
                "event": {
                    "sequence": event.sequence,
                    "event_kind": event.event_kind,
                    "event_schema_version": event.event_schema_version,
                    "payload_schema_version": event.payload_schema_version,
                    "action_key": event.action_key,
                    "subject_key": scene.subject_key,
                    "subject_profile_version": scene.subject_profile_version,
                    "activity_key": scene.activity_key,
                    "activity_contract_version": scene.activity_contract_version,
                    "renderer_key": scene.renderer_key,
                    "renderer_version": scene.renderer_version,
                    "scene_id": str(scene.id),
                    "scene_version": event.resulting_scene_version,
                    "action_payload": action_payload,
                    "validation": validation,
                },
            },
            workspace={
                "snapshot_schema_version": snapshot.snapshot_schema_version,
                "latest_event_sequence": snapshot.latest_event_sequence,
                "last_tutor_observation_sequence": runtime.last_tutor_observation_sequence,
                "current_scene_id": None if snapshot.current_scene_id is None else str(snapshot.current_scene_id),
                "current_scene_version": snapshot.current_scene_version,
                "active_subject_key": snapshot.active_subject_key,
                "active_activity_key": snapshot.active_activity_key,
                "state": dict(snapshot.state_payload),
            },
        )

    def _resolve_source_contract(
        self,
        *,
        event: StudioEvent,
        scene: StudioScene,
        interaction: StudioStudentInteraction,
    ) -> tuple[dict[str, object], dict[str, object] | None]:
        if event.actor != "STUDENT" or event.action_key is None:
            raise StudioInteractionSourceError("Studio interaction source must be a Student Activity action.")
        if event.subject_key != scene.subject_key or event.activity_key != scene.activity_key:
            raise StudioInteractionSourceError("Studio interaction source Event does not match its Scene contract.")
        try:
            activity = self._subject_registry.resolve_activity(
                scene.subject_key,
                scene.subject_profile_version,
                scene.activity_key,
                scene.activity_contract_version,
            )
            renderer = self._subject_registry.resolve_renderer(
                scene.subject_key,
                scene.subject_profile_version,
                scene.renderer_key,
                scene.renderer_version,
            )
            if activity.renderer_key != renderer.renderer_key or activity.renderer_version != renderer.renderer_version:
                raise SubjectCapabilityError("Activity and Renderer exact-version relation is unsupported.")
            action = self._subject_registry.resolve_action(
                scene.subject_key,
                scene.subject_profile_version,
                scene.activity_key,
                scene.activity_contract_version,
                event.action_key,
            )
        except SubjectCapabilityError as error:
            raise StudioInteractionSourceError(str(error)) from error
        if action.interaction_policy is not InteractionPolicy.TUTOR_TRIGGERING or action.interaction_kind != interaction.interaction_kind:
            raise StudioInteractionSourceError("Studio interaction is not owned by its triggering Action contract.")
        if event.event_kind != action.event_kind or event.event_schema_version != action.event_schema_version:
            raise StudioInteractionSourceError("Studio interaction Event does not match its Action contract.")
        if event.payload_schema_version != action.payload_schema_version:
            raise StudioInteractionSourceError("Studio interaction payload schema is unsupported by its Action contract.")
        payload = dict(event.payload)
        action_payload = payload.get("action")
        validation = payload.get("validation")
        if not isinstance(action_payload, dict):
            raise StudioInteractionSourceError("Studio interaction source lacks its typed action payload.")
        if validation is not None and not isinstance(validation, dict):
            raise StudioInteractionSourceError("Studio interaction validation result is malformed.")
        try:
            self._subject_registry.validate_subject_event(
                subject_key=scene.subject_key,
                subject_profile_version=scene.subject_profile_version,
                activity_key=scene.activity_key,
                activity_version=scene.activity_contract_version,
                action_key=event.action_key,
                payload_schema_version=event.payload_schema_version,
                payload=action_payload,
            )
        except SubjectCapabilityError as error:
            raise StudioInteractionSourceError(str(error)) from error
        return dict(action_payload), self._canonical_validation_result(
            validation=validation,
            semantic_validation_policy=action.semantic_validation_policy,
            registered_action_keys={registered.action_key for registered in activity.actions},
        )

    @staticmethod
    def _canonical_validation_result(
        *,
        validation: object,
        semantic_validation_policy: SemanticValidationPolicy,
        registered_action_keys: set[str],
    ) -> dict[str, object] | None:
        if semantic_validation_policy is SemanticValidationPolicy.NONE:
            if validation is not None:
                raise StudioInteractionSourceError("Studio interaction Action does not permit a validation result.")
            return None
        if not isinstance(validation, dict) or set(validation) != {"status", "feedback_code", "next_action_keys"}:
            raise StudioInteractionSourceError("Studio interaction validation result must use the bounded registered envelope.")
        raw_next_actions = validation["next_action_keys"]
        if not isinstance(raw_next_actions, list):
            raise StudioInteractionSourceError("Studio interaction validation next actions must be a list.")
        try:
            result = ValidationResult(
                status=ValidationStatus(validation["status"]),
                feedback_code=validation["feedback_code"],
                next_action_keys=tuple(raw_next_actions),
            )
        except (TypeError, ValueError) as error:
            raise StudioInteractionSourceError("Studio interaction validation result is invalid.") from error
        if not set(result.next_action_keys).issubset(registered_action_keys):
            raise StudioInteractionSourceError("Studio interaction validation next actions are unsupported.")
        return {
            "status": result.status.value,
            "feedback_code": result.feedback_code,
            "next_action_keys": list(result.next_action_keys),
        }

    def _model_payload(
        self,
        context: StudioInteractionTutorContext,
        *,
        workspace_context: object | None = None,
    ) -> dict[str, object]:
        """Use the shared strict Tutor contract without fabricating a Chat question."""

        encoded_context = context.as_model_payload()
        encoded_size = len(json.dumps(encoded_context, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        if encoded_size > MAX_INTERACTION_TUTOR_CONTEXT_BYTES:
            raise StudioInteractionSourceError("Studio interaction Tutor context exceeds its bounded capacity.")
        # Import here to avoid making the accepted Studio state boundary depend
        # on Tutor initialization merely because it persists interactions.
        from services.tutor.runtime import TUTOR_SHARED_INSTRUCTIONS

        workspace_payload = (
            workspace_context.as_model_payload()
            if callable(getattr(workspace_context, "as_model_payload", None))
            else None
        )
        workspace_input = (
            "\n\nStudio Workspace Context (current authoritative Workspace state; unseen Events are meaningful "
            "Student actions since the last successful Tutor observation):\n"
            f"{json.dumps(workspace_payload, ensure_ascii=False)}\n"
            "The Canvas interaction above remains the distinct current turn even when its source Event is already observed."
            if workspace_payload is not None
            else ""
        )

        return {
            "instructions": TUTOR_SHARED_INSTRUCTIONS,
            "input": (
                "Canvas-originated Studio interaction (server-owned bounded semantic control; no Chat Student message exists):\n"
                f"{json.dumps(encoded_context, ensure_ascii=False)}\n\n"
                "Respond naturally to the persisted semantic action and current Workspace state. "
                "Do not invent a Student question, explanation, reasoning, or source message. "
                f"The result is internal and not yet a delivered Tutor turn.{workspace_input}"
            ),
            "max_output_tokens": get_settings().tutor_max_output_tokens,
            "response_schema": TUTOR_OUTPUT_RESPONSE_SCHEMA,
            "studio_interaction_context": encoded_context,
            "studio_workspace_context": workspace_payload,
        }

    @staticmethod
    def _validate_tutor_output(result: ModelResult) -> None:
        if "workspace_intent" not in result.output:
            raise StudioInteractionTutorOutputError("Tutor turn v9 output is missing required workspace_intent.")
        try:
            parse_workspace_intent(result.output["workspace_intent"])
        except WorkspaceIntentContractError as error:
            raise StudioInteractionTutorOutputError("Tutor workspace intent violates the current v9 contract.") from error

    def _verify_execution_provenance(
        self,
        *,
        execution_id: UUID | None,
        interaction_id: UUID,
        student_id: UUID,
        learning_session_id: UUID,
    ) -> None:
        if execution_id is None:
            raise StudioInteractionTutorOutputError("Tutor Gateway did not return durable execution provenance.")
        with Session(self._bind) as verification_session:
            self._verify_execution_provenance_in_session(
                verification_session,
                execution_id=execution_id,
                interaction_id=interaction_id,
                student_id=student_id,
                learning_session_id=learning_session_id,
            )

    @staticmethod
    def _verify_execution_provenance_in_session(
        session: Session,
        *,
        execution_id: UUID | None,
        interaction_id: UUID,
        student_id: UUID,
        learning_session_id: UUID,
    ) -> None:
        if execution_id is None:
            raise StudioInteractionTutorOutputError("Tutor Gateway did not return durable execution provenance.")
        execution = session.get(AIExecution, execution_id)
        if (
            execution is None
            or execution.task != ModelTask.TUTOR.value
            or execution.operation_type != STUDIO_INTERACTION_TUTOR_OPERATION
            or execution.operation_id != interaction_id
            or execution.student_id != student_id
            or execution.learning_session_id != learning_session_id
            or execution.source_message_id is not None
            or execution.success is not True
        ):
            raise StudioInteractionTutorOutputError("Tutor Gateway execution provenance is incomplete or inconsistent.")

    @staticmethod
    def _workspace_audit(raw_intent: object, workspace_context: object) -> dict[str, object]:
        """Validate the shared v9 field while keeping routing failures non-terminal.

        The actual Router is deliberately deferred to the normal Workspace
        authority owner; no Canvas endpoint can execute an Activity, Renderer,
        or Specialist merely by returning an intent.
        """

        try:
            intent = parse_workspace_intent(raw_intent)
        except WorkspaceIntentContractError:
            return {
                "intent_status": "INVALID",
                "intent": None,
                "decision": WorkspaceExecutionDecision(
                    version="workspace-execution-decision-v1", status=WorkspaceDecisionStatus.FALLBACK,
                    mode=None, reason_code="INTENT_INVALID", target_scene_id=None, target_source_reference=None,
                ).as_audit_payload(),
            }
        if intent is None:
            return {
                "intent_status": "ABSENT",
                "intent": None,
                "decision": WorkspaceExecutionDecision(
                    version="workspace-execution-decision-v1", status=WorkspaceDecisionStatus.NO_CHANGE,
                    mode=None, reason_code="NO_WORKSPACE_INTENT", target_scene_id=None, target_source_reference=None,
                ).as_audit_payload(),
            }
        scene = getattr(workspace_context, "current_scene_capability", None)
        decision = route_workspace_intent(
            intent,
            WorkspaceAuthorityContext(
                active_scene_id=None if scene is None else str(scene.scene_id),
                active_subject_key=None if scene is None else scene.subject_key,
                active_scene=(
                    None if scene is None else ActiveSceneCapability(
                        scene_id=str(scene.scene_id), subject_key=scene.subject_key,
                        subject_profile_version=scene.subject_profile_version, activity_key=scene.activity_key,
                        activity_version=scene.activity_version, renderer_key=scene.renderer_key,
                        renderer_version=scene.renderer_version, source_references=scene.source_references,
                    )
                ),
                authorized_source_references=(),
                registry=production_subject_registry(),
                current_profile_versions=PRODUCTION_CURRENT_PROFILE_VERSIONS,
            ),
        )
        return {
            "intent_status": "VALID",
            "intent": intent.model_dump(mode="json"),
            "decision": decision.as_audit_payload(),
        }
