"""Strict, application-owned contracts for Canvas Specialist execution."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
from collections.abc import Callable
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.platform.db.models import Job, LearningMessage, LearningSession, StudioCanvasSpecialistRun, StudioRuntime, StudioScene
from services.platform.jobs import enqueue_job
from services.studio.visual_order import contains_implementation_control


CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION = "canvas-specialist-process-proposal-v1"
PROCESS_EXECUTION_CAPABILITY_PACK_IDENTITY = "process-capability-pack-v1"
CANVAS_SPECIALIST_PROCESS_PROPOSAL_V2_SCHEMA_VERSION = "canvas-specialist-process-proposal-v2"
PROCESS_EXECUTION_CAPABILITY_PACK_V2_IDENTITY = "process-capability-pack-v2"
CANVAS_SPECIALIST_SPATIAL_PROPOSAL_SCHEMA_VERSION = "canvas-specialist-spatial-proposal-v1"
CANVAS_SPECIALIST_MATH_VISUALIZATION_PROPOSAL_SCHEMA_VERSION = "canvas-specialist-math-visualization-proposal-v1"
CANVAS_SPECIALIST_MATH_INPUT_PROPOSAL_SCHEMA_VERSION = "canvas-specialist-math-input-proposal-v1"
SPATIAL_CAPABILITY_PACK_IDENTITY = "canvas-spatial-capability-pack-v1"
MATH_VISUALIZATION_CAPABILITY_PACK_IDENTITY = "canvas-math-visualization-capability-pack-v1"
MATH_INPUT_CAPABILITY_PACK_IDENTITY = "canvas-math-input-capability-pack-v1"
FROZEN_COMPOSITION_PACK_V1_SCHEMA_VERSION = "frozen-composition-pack-v1"
FROZEN_COMPOSITION_PACK_V2_SCHEMA_VERSION = "frozen-composition-pack-v2"
CANVAS_SPECIALIST_COMPOSE_JOB = "studio.canvas_specialist.compose.v1"
CANVAS_SPECIALIST_DEADLINE = timedelta(minutes=2)

CAPABILITY_SCHEMA_VERSIONS = {
    PROCESS_EXECUTION_CAPABILITY_PACK_IDENTITY: CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION,
    PROCESS_EXECUTION_CAPABILITY_PACK_V2_IDENTITY: CANVAS_SPECIALIST_PROCESS_PROPOSAL_V2_SCHEMA_VERSION,
    SPATIAL_CAPABILITY_PACK_IDENTITY: CANVAS_SPECIALIST_SPATIAL_PROPOSAL_SCHEMA_VERSION,
    MATH_VISUALIZATION_CAPABILITY_PACK_IDENTITY: CANVAS_SPECIALIST_MATH_VISUALIZATION_PROPOSAL_SCHEMA_VERSION,
    MATH_INPUT_CAPABILITY_PACK_IDENTITY: CANVAS_SPECIALIST_MATH_INPUT_PROPOSAL_SCHEMA_VERSION,
}

class _Stage(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    semantic_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    label: str = Field(min_length=1, max_length=80)
    detail: str | None = Field(..., max_length=300)
    support_ids: list[str] = Field(min_length=1, max_length=8)
    art_handle: str | None = Field(..., max_length=64)


class _Relation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    relation_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    source_semantic_key: str = Field(min_length=1, max_length=64)
    target_semantic_key: str = Field(min_length=1, max_length=64)
    label: str | None = Field(..., max_length=120)
    support_ids: list[str] = Field(min_length=1, max_length=8)


class CanvasSpecialistProcessProposal(BaseModel):
    """Untrusted semantic proposal only; never a Scene or renderer instruction."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: Literal[CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION]
    pattern: Literal["PROCESS"]
    topology: Literal["SEQUENCE", "CYCLE"]
    title: str = Field(min_length=1, max_length=120)
    subtitle: str | None = Field(..., max_length=180)
    stages: list[_Stage] = Field(min_length=2, max_length=8)
    relations: list[_Relation] = Field(..., max_length=8)
    text_equivalent: str = Field(min_length=1, max_length=1000)
    focus_intent: Literal["FOCUS_STAGE", "FOCUS_RELATION"] | None = Field(...)
    motion_intents: list[Literal["REVEAL_IN_ORDER", "TRACE_CYCLE"]] = Field(..., max_length=8)
    interaction_affordances: list[Literal["FOCUS_OBJECT", "DEEMPHASIZE_OTHERS", "REVEAL_OBJECT_DETAIL", "TRACE_RELATION", "TRANSITION_FOCUS"]] = Field(..., max_length=8)

    @field_validator("motion_intents", "interaction_affordances")
    @classmethod
    def unique_values(cls, values: list[str]) -> list[str]:
        if len({value.casefold() for value in values}) != len(values):
            raise ValueError("proposal values must be unique")
        return values

    @model_validator(mode="after")
    def bounded_semantics_only(self) -> "CanvasSpecialistProcessProposal":
        keys = [stage.semantic_key for stage in self.stages]
        if len(set(keys)) != len(keys):
            raise ValueError("stage semantic keys must be unique")
        if len({relation.relation_key for relation in self.relations}) != len(self.relations):
            raise ValueError("relation keys must be unique")
        if any(relation.source_semantic_key not in keys or relation.target_semantic_key not in keys for relation in self.relations):
            raise ValueError("relations must reference proposal-local stage keys")
        text = " ".join(filter(None, [self.title, self.subtitle, self.text_equivalent, *(stage.label for stage in self.stages), *(stage.detail or "" for stage in self.stages), *(relation.label or "" for relation in self.relations)]))
        if contains_implementation_control(text):
            raise ValueError("proposal must not contain executable, URL, or engine instructions")
        return self


class CanvasSpecialistProcessProposalV2(CanvasSpecialistProcessProposal):
    """Additive semantic-motion proposal; V1 remains the durable historical contract."""
    version: Literal[CANVAS_SPECIALIST_PROCESS_PROPOSAL_V2_SCHEMA_VERSION]
    motion_intents: list[Literal["REVEAL_IN_ORDER", "TRACE_SEQUENCE", "TRACE_CYCLE", "TRANSITION_FOCUS", "EMPHASIZE_RELATION"]] = Field(..., max_length=8)


class _SemanticObject(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    semantic_key: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_-]*$")
    label: str = Field(min_length=1, max_length=40)
    support_ids: list[str] = Field(min_length=1, max_length=8)


class _SpatialTarget(_SemanticObject):
    relation: Literal["INSIDE", "MATCH", "GROUP"]


class _InitialPlacement(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    object_semantic_key: str = Field(min_length=1, max_length=64)
    target_semantic_key: str | None = Field(..., max_length=64)


class CanvasSpecialistSpatialProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: Literal[CANVAS_SPECIALIST_SPATIAL_PROPOSAL_SCHEMA_VERSION]
    pattern: Literal["SPATIAL_MANIPULATION"]
    title: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=240)
    objects: list[_SemanticObject] = Field(min_length=1, max_length=4)
    targets: list[_SpatialTarget] = Field(min_length=1, max_length=4)
    initial_placements: list[_InitialPlacement] = Field(min_length=1, max_length=4)
    interaction_affordances: list[Literal["PLACE_OBJECT"]] = Field(min_length=1, max_length=1)
    text_equivalent: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def semantic_only(self) -> "CanvasSpecialistSpatialProposal":
        object_ids = [item.semantic_key for item in self.objects]
        target_ids = [item.semantic_key for item in self.targets]
        if len(set(object_ids)) != len(object_ids) or len(set(target_ids)) != len(target_ids) or set(object_ids) & set(target_ids):
            raise ValueError("Spatial semantic identities must be unique")
        if {item.object_semantic_key for item in self.initial_placements} != set(object_ids):
            raise ValueError("Every spatial object needs one initial placement")
        if len({item.object_semantic_key for item in self.initial_placements}) != len(self.initial_placements):
            raise ValueError("Spatial initial placements must be unique")
        if any(item.target_semantic_key is not None and item.target_semantic_key not in target_ids for item in self.initial_placements):
            raise ValueError("Initial placement target is unknown")
        if contains_implementation_control(" ".join([self.title, self.prompt, self.text_equivalent, *(item.label for item in self.objects), *(item.label for item in self.targets)])):
            raise ValueError("proposal must not contain implementation instructions")
        return self


class _IntegerRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minimum: int = Field(ge=-4, le=4)
    maximum: int = Field(ge=-4, le=4)

    @model_validator(mode="after")
    def ordered(self) -> "_IntegerRange":
        if self.minimum >= self.maximum:
            raise ValueError("Mathematical range must increase")
        return self


class _ConstructionPoint(_SemanticObject):
    initial_x: int = Field(ge=-4, le=4)
    initial_y: int = Field(ge=-4, le=4)


class _TargetPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: int = Field(ge=-4, le=4)
    y: int = Field(ge=-4, le=4)
    support_ids: list[str] = Field(min_length=1, max_length=8)


class CanvasSpecialistMathVisualizationProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: Literal[CANVAS_SPECIALIST_MATH_VISUALIZATION_PROPOSAL_SCHEMA_VERSION]
    pattern: Literal["MATH_VISUALIZATION"]
    title: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=240)
    point: _ConstructionPoint
    target: _TargetPoint
    x_range: _IntegerRange
    y_range: _IntegerRange
    interaction_affordances: list[Literal["PLACE_POINT", "SUBMIT_CONSTRUCTION"]] = Field(min_length=2, max_length=2)
    text_equivalent: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def semantic_only(self) -> "CanvasSpecialistMathVisualizationProposal":
        if set(self.interaction_affordances) != {"PLACE_POINT", "SUBMIT_CONSTRUCTION"}:
            raise ValueError("Both construction interactions are required")
        if (self.x_range.minimum, self.x_range.maximum, self.y_range.minimum, self.y_range.maximum) != (-4, 4, -4, 4):
            raise ValueError("The application supports the exact -4 to 4 coordinate plane")
        for x, y in ((self.point.initial_x, self.point.initial_y), (self.target.x, self.target.y)):
            if not self.x_range.minimum <= x <= self.x_range.maximum or not self.y_range.minimum <= y <= self.y_range.maximum:
                raise ValueError("Point is outside the semantic axes")
        if contains_implementation_control(" ".join((self.title, self.prompt, self.point.label, self.text_equivalent))):
            raise ValueError("proposal must not contain implementation instructions")
        return self


class CanvasSpecialistMathInputProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: Literal[CANVAS_SPECIALIST_MATH_INPUT_PROPOSAL_SCHEMA_VERSION]
    pattern: Literal["MATH_INPUT"]
    title: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=240)
    initial_latex: str = Field(max_length=120)
    expected_form: Literal["LATEX"]
    expression_max_length: int = Field(ge=1, le=120)
    support_ids: list[str] = Field(min_length=1, max_length=8)
    interaction_affordances: list[Literal["SUBMIT_EXPRESSION"]] = Field(min_length=1, max_length=1)
    text_equivalent: str = Field(min_length=1, max_length=600)

    @model_validator(mode="after")
    def semantic_only(self) -> "CanvasSpecialistMathInputProposal":
        if len(self.initial_latex) > self.expression_max_length:
            raise ValueError("Initial expression exceeds its semantic bound")
        if contains_implementation_control(" ".join((self.title, self.prompt, self.text_equivalent))):
            raise ValueError("proposal must not contain implementation instructions")
        return self


def proposal_contract(capability_identity: str, schema_version: str):
    pairs = {
        (PROCESS_EXECUTION_CAPABILITY_PACK_IDENTITY, CANVAS_SPECIALIST_PROCESS_PROPOSAL_SCHEMA_VERSION): CanvasSpecialistProcessProposal,
        (PROCESS_EXECUTION_CAPABILITY_PACK_V2_IDENTITY, CANVAS_SPECIALIST_PROCESS_PROPOSAL_V2_SCHEMA_VERSION): CanvasSpecialistProcessProposalV2,
        (SPATIAL_CAPABILITY_PACK_IDENTITY, CANVAS_SPECIALIST_SPATIAL_PROPOSAL_SCHEMA_VERSION): CanvasSpecialistSpatialProposal,
        (MATH_VISUALIZATION_CAPABILITY_PACK_IDENTITY, CANVAS_SPECIALIST_MATH_VISUALIZATION_PROPOSAL_SCHEMA_VERSION): CanvasSpecialistMathVisualizationProposal,
        (MATH_INPUT_CAPABILITY_PACK_IDENTITY, CANVAS_SPECIALIST_MATH_INPUT_PROPOSAL_SCHEMA_VERSION): CanvasSpecialistMathInputProposal,
    }
    proposal = pairs.get((capability_identity, schema_version))
    if proposal is None:
        raise ValueError("unsupported Canvas Specialist execution identity")
    return proposal


def frozen_pack_identity_is_valid(pack: dict[str, object], capability_identity: str) -> bool:
    return (pack.get("version"), capability_identity) in {
        (FROZEN_COMPOSITION_PACK_V1_SCHEMA_VERSION, PROCESS_EXECUTION_CAPABILITY_PACK_IDENTITY),
        (FROZEN_COMPOSITION_PACK_V2_SCHEMA_VERSION, PROCESS_EXECUTION_CAPABILITY_PACK_V2_IDENTITY),
        ("frozen-composition-pack-v3", SPATIAL_CAPABILITY_PACK_IDENTITY),
        ("frozen-composition-pack-v3", MATH_VISUALIZATION_CAPABILITY_PACK_IDENTITY),
        ("frozen-composition-pack-v3", MATH_INPUT_CAPABILITY_PACK_IDENTITY),
    }


class CanvasSpecialistAdmissionError(ValueError):
    pass


def validate_proposal_against_frozen_pack(proposal: BaseModel, pack: dict[str, object]) -> None:
    """Bound semantic-support validation; this is not general factual inference."""
    if pack.get("pattern") != proposal.pattern or pack.get("topology") != getattr(proposal, "topology", None):
        raise ValueError("proposal does not match frozen pattern/topology")
    capability = pack.get("capability_pack")
    if not isinstance(capability, dict):
        raise ValueError("proposal has no exact capability pack")
    if proposal.pattern != "PROCESS":
        alignment = pack.get("semantic_alignment")
        if not isinstance(alignment, dict):
            raise ValueError("frozen semantic alignment is invalid")
        supported = {item.get("id") for key in ("required_semantics", "required_relations") for item in alignment.get(key, []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
        if isinstance(proposal, CanvasSpecialistSpatialProposal):
            claimed = {support for item in (*proposal.objects, *proposal.targets) for support in item.support_ids}
            low, high = capability.get("object_count_limit", []); target_low, target_high = capability.get("target_count_limit", [])
            if not low <= len(proposal.objects) <= high or not target_low <= len(proposal.targets) <= target_high:
                raise ValueError("spatial proposal exceeds frozen bounds")
            if any(item.relation not in capability.get("allowed_relations", []) for item in proposal.targets):
                raise ValueError("spatial relation is not enabled")
            if any(len(item.label) > capability.get("label_max_length", 0) for item in (*proposal.objects, *proposal.targets)):
                raise ValueError("spatial label exceeds the frozen bound")
        elif isinstance(proposal, CanvasSpecialistMathVisualizationProposal):
            claimed = {*proposal.point.support_ids, *proposal.target.support_ids}
            low, high = capability.get("coordinate_bounds", [])
            if proposal.x_range.minimum < low or proposal.x_range.maximum > high or proposal.y_range.minimum < low or proposal.y_range.maximum > high:
                raise ValueError("mathematical construction exceeds frozen bounds")
            if capability.get("construction_family") != "CARTESIAN_POINT":
                raise ValueError("mathematical construction family is not enabled")
            if len(proposal.point.label) > capability.get("label_max_length", 0):
                raise ValueError("mathematical label exceeds the frozen bound")
        elif isinstance(proposal, CanvasSpecialistMathInputProposal):
            claimed = set(proposal.support_ids)
            if capability.get("input_representation") != proposal.expected_form or proposal.expression_max_length > capability.get("expression_max_length", 0):
                raise ValueError("math input form exceeds frozen bounds")
        else:
            raise ValueError("unsupported Canvas proposal")
        if claimed != supported:
            raise ValueError("proposal support is not covered by the frozen semantic alignment")
        allowed = pack.get("allowed_affordances")
        if not isinstance(allowed, list) or not set(proposal.interaction_affordances).issubset(set(allowed)):
            raise ValueError("proposal affordance is not allowed by the frozen pack")
        return
    limits = capability.get("process_stage_limit") if isinstance(capability, dict) else None
    if not isinstance(limits, list) or len(limits) != 2 or not limits[0] <= len(proposal.stages) <= limits[1]:
        raise ValueError("proposal exceeds frozen stage limit")
    alignment = pack.get("semantic_alignment")
    if not isinstance(alignment, dict):
        raise ValueError("frozen semantic alignment is invalid")
    semantic_ids = {item.get("id") for item in alignment.get("required_semantics", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
    relation_ids = {item.get("id") for item in alignment.get("required_relations", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
    stage_claimed = {identifier for stage in proposal.stages for identifier in stage.support_ids}
    relation_claimed = {identifier for relation in proposal.relations for identifier in relation.support_ids}
    if stage_claimed != semantic_ids or (relation_claimed != relation_ids if relation_ids else not relation_claimed.issubset(semantic_ids)):
        raise ValueError("proposal support is not covered by the frozen semantic alignment")
    forbidden = [value.casefold() for value in alignment.get("must_not_imply", []) if isinstance(value, str)]
    proposal_text = " ".join(filter(None, [proposal.title, proposal.subtitle, proposal.text_equivalent, *(stage.label for stage in proposal.stages), *(stage.detail or "" for stage in proposal.stages), *(relation.label or "" for relation in proposal.relations)])).casefold()
    if any(value in proposal_text for value in forbidden):
        raise ValueError("proposal implies forbidden frozen meaning")
    allowed = pack.get("allowed_affordances")
    if not isinstance(allowed, list) or not set(proposal.interaction_affordances).issubset(set(allowed)):
        raise ValueError("proposal affordance is not allowed by the frozen pack")
    allowed_motion = pack.get("allowed_motion_intents", [])
    if not isinstance(allowed_motion, list) or not set(proposal.motion_intents).issubset(set(allowed_motion)):
        raise ValueError("proposal motion is not allowed by the frozen pack")
    if proposal.topology == "SEQUENCE" and "TRACE_CYCLE" in proposal.motion_intents:
        raise ValueError("proposal motion is incompatible with topology")
    if proposal.topology == "CYCLE" and "TRACE_SEQUENCE" in proposal.motion_intents:
        raise ValueError("proposal motion is incompatible with topology")
    allowed_art_handles = pack.get("allowed_art_handles", [])
    if not isinstance(allowed_art_handles, list) or any(
        stage.art_handle is not None and stage.art_handle not in allowed_art_handles
        for stage in proposal.stages
    ):
        raise ValueError("proposal requests artwork not enabled by the frozen pack")


def admit_committed_visual_order(session: Session, *, student_id: UUID, learning_session_id: UUID, source_message_id: UUID, now: datetime | None = None, before_run_create: Callable[[], None] | None = None) -> StudioCanvasSpecialistRun | None:
    """Atomically admit one executable committed order; all non-admitted paths are no-ops."""
    unguarded_message = session.get(LearningMessage, source_message_id)
    learning_session = session.get(LearningSession, learning_session_id)
    if unguarded_message is None or learning_session is None or learning_session.student_id != student_id:
        raise CanvasSpecialistAdmissionError("SOURCE_LINEAGE_INVALID")
    runtime = session.execute(select(StudioRuntime).where(StudioRuntime.student_id == student_id, StudioRuntime.learning_session_id == learning_session_id).with_for_update()).scalar_one_or_none()
    if runtime is None:
        raise CanvasSpecialistAdmissionError("STUDIO_RUNTIME_INVALID")
    message = session.execute(select(LearningMessage).where(LearningMessage.id == source_message_id, LearningMessage.session_id == learning_session_id, LearningMessage.role == "tutor").with_for_update()).scalar_one_or_none()
    if message is None:
        raise CanvasSpecialistAdmissionError("SOURCE_LINEAGE_INVALID")
    visual = message.payload.get("workspace_visual") if isinstance(message.payload, dict) else None
    if not isinstance(visual, dict) or visual.get("status") != "ADMITTED":
        return None
    digest = visual.get("order_digest")
    pack = visual.get("frozen_composition_pack")
    if not isinstance(digest, str) or len(digest) != 64 or not isinstance(pack, dict):
        raise CanvasSpecialistAdmissionError("FROZEN_PACK_INVALID")
    if sha256(json.dumps(pack, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest() != digest:
        raise CanvasSpecialistAdmissionError("ORDER_DIGEST_INVALID")
    capability = pack.get("capability_pack")
    if not isinstance(capability, dict) or capability.get("identity") not in CAPABILITY_SCHEMA_VERSIONS:
        return None
    admitted_messages = session.scalars(select(LearningMessage).where(LearningMessage.session_id == learning_session_id, LearningMessage.role == "tutor").order_by(LearningMessage.created_at.desc(), LearningMessage.id.asc()).with_for_update())
    newest = next((candidate for candidate in admitted_messages if isinstance(candidate.payload, dict) and isinstance(candidate.payload.get("workspace_visual"), dict) and candidate.payload["workspace_visual"].get("status") == "ADMITTED"), None)
    if newest is None or newest.id != message.id:
        return None
    capability_identity = capability["identity"]
    if not frozen_pack_identity_is_valid(pack, capability_identity):
        raise CanvasSpecialistAdmissionError("FROZEN_PACK_IDENTITY_INVALID")
    schema_version = CAPABILITY_SCHEMA_VERSIONS[capability_identity]
    existing = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.source_message_id == source_message_id, StudioCanvasSpecialistRun.order_digest == digest, StudioCanvasSpecialistRun.capability_profile_version == capability_identity)).scalar_one_or_none()
    if existing is not None:
        return existing
    # A later admitted order is the sole current composition intent. Pending
    # work is made unclaimable; a genuinely in-flight call may return, but its
    # settlement is permanently barred by the Run's superseded state.
    prior_runs = session.scalars(
        select(StudioCanvasSpecialistRun)
        .join(LearningMessage, StudioCanvasSpecialistRun.source_message_id == LearningMessage.id)
        .where(
            StudioCanvasSpecialistRun.studio_runtime_id == runtime.id,
            StudioCanvasSpecialistRun.status.in_(("PENDING", "RUNNING", "COMPLETED")),
            StudioCanvasSpecialistRun.scene_id.is_(None),
            StudioCanvasSpecialistRun.source_message_id != message.id,
        )
        .with_for_update()
    )
    superseded_at = now or datetime.now(UTC)
    for prior in prior_runs:
        prior.status = "SUPERSEDED"
        prior.failure_metadata = {"code": "SUPERSEDED_BY_NEWER_ADMITTED_ORDER", "successor_order_digest": digest}
        prior.completed_at = superseded_at
        if prior.job_id is not None:
            prior_job = session.get(Job, prior.job_id, with_for_update=True)
            if prior_job is not None and prior_job.status == "PENDING":
                prior_job.status = "FAILED"
                prior_job.completed_at = superseded_at
                prior_job.last_error = "Superseded by a newer admitted Canvas Specialist order."
    key = f"canvas-specialist:{source_message_id}:{digest}:{capability_identity}"
    job = enqueue_job(session, job_type=CANVAS_SPECIALIST_COMPOSE_JOB, payload={"student_id": str(student_id), "learning_session_id": str(learning_session_id), "source_message_id": str(source_message_id), "order_digest": digest, "capability_identity": capability_identity}, idempotency_key=key, max_attempts=2)
    if before_run_create is not None:
        before_run_create()
    try:
        with session.begin_nested():
            active_scene = session.execute(select(StudioScene).where(StudioScene.studio_runtime_id == runtime.id, StudioScene.status == "ACTIVE").with_for_update()).scalar_one_or_none()
            subject_key = "PROCESS" if capability_identity.startswith("process-") else "MATH"
            run = StudioCanvasSpecialistRun(studio_runtime_id=runtime.id, student_id=student_id, learning_session_id=learning_session_id, source_message_id=source_message_id, scene_id=None, base_scene_id=None if active_scene is None else active_scene.id, base_scene_version=0 if active_scene is None else active_scene.scene_version, subject_key=subject_key, capability_profile_version=capability_identity, status="PENDING", job_id=job.id, output_schema_version=schema_version, accepted_scene_version=None, deadline_at=(now or datetime.now(UTC)) + CANVAS_SPECIALIST_DEADLINE, order_digest=digest)
            session.add(run)
            session.flush()
            return run
    except IntegrityError:
        existing = session.execute(select(StudioCanvasSpecialistRun).where(StudioCanvasSpecialistRun.source_message_id == source_message_id, StudioCanvasSpecialistRun.order_digest == digest, StudioCanvasSpecialistRun.capability_profile_version == capability_identity)).scalar_one_or_none()
        if existing is None:
            raise CanvasSpecialistAdmissionError("EXECUTION_IDENTITY_CONFLICT") from None
        return existing
