"""Deterministic, versioned conversational Concept registry helpers.

This is a reference mapping only.  It never creates learner truth and a
missing/invalid registry is deliberately indistinguishable from no mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.intelligence.subjects import is_supported_broad_subject
from services.platform.db.models import CandidateEvent, CanonicalConceptRegistryRecord, LearningEvidence, LearningEvent, LearningSegment, LearningSegmentConceptLink, LearnerPattern, PatternEvidence
from services.tutor.teaching_methods import TEACHING_METHOD_REGISTRY_VERSION, is_supported_teaching_method


class ConceptRegistryValidationError(ValueError):
    """A registry cannot deterministically resolve its own aliases."""


@dataclass(frozen=True)
class ConceptResolution:
    status: str
    concept_key: str | None
    registry_version: str | None


@dataclass(frozen=True)
class CanonicalConcept:
    concept_key: str
    broad_subject: str
    display_name_en: str
    display_name_ar: str
    aliases: tuple[str, ...]


class CanonicalConceptRegistry:
    def __init__(self, *, version: str, concepts: tuple[CanonicalConcept, ...]) -> None:
        self.version = version
        self.concepts = concepts
        aliases: dict[tuple[str, str], str] = {}
        for concept in concepts:
            if not is_supported_broad_subject(concept.broad_subject):
                raise ConceptRegistryValidationError("Concept subject is outside the Broad Subject registry.")
            values = (*concept.aliases, concept.concept_key)
            for value in values:
                normalized = normalize_concept_ref(value)
                if not normalized:
                    raise ConceptRegistryValidationError("Concept aliases must be non-empty after normalization.")
                key = (concept.broad_subject, normalized)
                prior = aliases.get(key)
                if prior is not None and prior != concept.concept_key:
                    raise ConceptRegistryValidationError("Concept aliases collide after normalization within a Broad Subject.")
                aliases[key] = concept.concept_key
        self._aliases = aliases

    @classmethod
    def from_payload(cls, *, version: str, payload: object) -> "CanonicalConceptRegistry":
        if not isinstance(version, str) or not version.strip() or not isinstance(payload, Mapping):
            raise ConceptRegistryValidationError("Concept Registry requires a version and object payload.")
        raw_concepts = payload.get("concepts")
        if not isinstance(raw_concepts, list):
            raise ConceptRegistryValidationError("Concept Registry payload requires concepts.")
        concepts: list[CanonicalConcept] = []
        keys: set[str] = set()
        for raw in raw_concepts:
            if not isinstance(raw, Mapping):
                raise ConceptRegistryValidationError("Concept entries must be objects.")
            values = {key: raw.get(key) for key in ("concept_key", "broad_subject", "display_name_en", "display_name_ar", "aliases")}
            if not all(isinstance(values[key], str) and values[key].strip() for key in ("concept_key", "broad_subject", "display_name_en", "display_name_ar")):
                raise ConceptRegistryValidationError("Concept entries require non-empty identity fields.")
            if not isinstance(values["aliases"], list) or not all(isinstance(item, str) and item.strip() for item in values["aliases"]):
                raise ConceptRegistryValidationError("Concept aliases must be non-empty strings.")
            concept_key = str(values["concept_key"])
            if concept_key in keys:
                raise ConceptRegistryValidationError("Concept keys must be unique.")
            keys.add(concept_key)
            concepts.append(CanonicalConcept(concept_key, str(values["broad_subject"]), str(values["display_name_en"]), str(values["display_name_ar"]), tuple(values["aliases"])))
        return cls(version=version, concepts=tuple(concepts))

    def resolve(self, *, subject: str | None, concept_ref: str | None) -> ConceptResolution:
        normalized = normalize_concept_ref(concept_ref)
        if subject is None or not normalized:
            return ConceptResolution("UNMAPPED", None, self.version)
        concept_key = self._aliases.get((subject, normalized))
        return ConceptResolution("MAPPED", concept_key, self.version) if concept_key else ConceptResolution("UNMAPPED", None, self.version)


def normalize_concept_ref(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = re.sub(r"[-_\s]+", " ", normalized)
    return " ".join(normalized.split())


def active_registry(session: Session) -> CanonicalConceptRegistry | None:
    """Load a validated active registry, failing open for optional history."""
    try:
        rows = session.scalars(
            select(CanonicalConceptRegistryRecord).where(
                CanonicalConceptRegistryRecord.is_active.is_(True)
            )
        ).all()
        if len(rows) != 1:
            return None
        row = rows[0]
        return None if row is None else CanonicalConceptRegistry.from_payload(version=row.version, payload=row.payload)
    except Exception:
        return None


def activate_registry(session: Session, *, registry_id: UUID) -> CanonicalConceptRegistryRecord:
    """Atomically replace the sole active reference registry without learner-data writes."""
    target = session.scalar(
        select(CanonicalConceptRegistryRecord)
        .where(CanonicalConceptRegistryRecord.id == registry_id)
        .with_for_update()
    )
    if target is None:
        raise ValueError("Canonical Concept Registry does not exist.")
    active_rows = session.scalars(
        select(CanonicalConceptRegistryRecord)
        .where(CanonicalConceptRegistryRecord.is_active.is_(True))
        .with_for_update()
    ).all()
    if target in active_rows:
        return target
    for row in active_rows:
        row.is_active = False
    session.flush()
    target.is_active = True
    session.flush()
    return target


def persist_primary_concept(
    session: Session,
    *,
    segment: LearningSegment,
    subject: str | None,
    concept_ref: object,
    conversation_subject_hint: str | None = None,
    preserve_existing: bool = False,
) -> None:
    """Persist optional conversational identity; unresolved identity remains safe."""
    if (
        segment.conversation_subject_hint is None
        and conversation_subject_hint is not None
        and is_supported_broad_subject(conversation_subject_hint)
    ):
        segment.conversation_subject_hint = conversation_subject_hint
    if preserve_existing and segment.primary_concept_key is not None:
        return
    if not isinstance(concept_ref, str) or not concept_ref.strip():
        return
    segment.primary_concept_ref = concept_ref.strip()[:128]
    registry = active_registry(session)
    mapping_subject = subject if is_supported_broad_subject(subject) else None
    resolution = registry.resolve(subject=mapping_subject, concept_ref=segment.primary_concept_ref) if registry else ConceptResolution("UNMAPPED", None, None)
    segment.primary_concept_key = resolution.concept_key
    segment.concept_registry_version = resolution.registry_version
    segment.concept_mapping_status = resolution.status
    session.flush()


def persist_related_concepts(session: Session, *, segment: LearningSegment, subject: str | None, concept_refs: list[object]) -> None:
    """Add only completed-Review mapped links; invalid/unmapped refs are ignored."""
    registry = active_registry(session)
    if registry is None or subject is None:
        return
    for raw in concept_refs:
        resolution = registry.resolve(subject=subject, concept_ref=raw if isinstance(raw, str) else None)
        if (
            resolution.concept_key is None
            or resolution.registry_version is None
            or resolution.concept_key == segment.primary_concept_key
        ):
            continue
        existing = session.scalars(select(LearningSegmentConceptLink).where(LearningSegmentConceptLink.segment_id == segment.id, LearningSegmentConceptLink.concept_key == resolution.concept_key)).first()
        if existing is None:
            session.add(LearningSegmentConceptLink(segment_id=segment.id, concept_key=resolution.concept_key, broad_subject=subject, registry_version=resolution.registry_version))
    session.flush()


def advisory_pattern_meaning(session: Session, *, pattern: LearnerPattern, concept_key: str) -> str | None:
    """Recover only validated, concise lineage needed in the Tutor's advisory context."""
    rows = session.execute(
        select(CandidateEvent).join(LearningEvent, LearningEvent.candidate_event_id == CandidateEvent.id)
        .join(LearningEvidence, LearningEvidence.event_id == LearningEvent.id)
        .join(PatternEvidence, PatternEvidence.evidence_id == LearningEvidence.id)
        .where(PatternEvidence.pattern_id == pattern.id)
        .order_by(PatternEvidence.observed_at.desc())
    ).scalars()
    for candidate in rows:
        payload = candidate.payload if isinstance(candidate.payload, dict) else {}
        if pattern.pattern_type == "strategy_effectiveness":
            method = is_supported_teaching_method(payload.get("strategy_key"), registry_version=payload.get("strategy_registry_version"))
            outcome = payload.get("observed_student_outcome")
            if method is not None and payload.get("strategy_registry_version") == TEACHING_METHOD_REGISTRY_VERSION and isinstance(outcome, str) and outcome.strip():
                return f"Concept: {concept_key}\nHistorical TeachingMethod: {method.value}\nValidated historical outcome: {outcome.strip()[:160]}\nPattern status: {pattern.status}\nAuthority: advisory; current Student behavior wins."
        if pattern.pattern_type == "misconception_recurrence":
            evidence = payload.get("misconception_evidence")
            if isinstance(evidence, dict) and isinstance(evidence.get("incorrect_model"), str) and evidence["incorrect_model"].strip():
                return f"Concept: {concept_key}\nHistorical misconception: {evidence['incorrect_model'].strip()[:240]}\nPattern status: {pattern.status}\nAuthority: advisory; verify against current Student behavior."
    return None
