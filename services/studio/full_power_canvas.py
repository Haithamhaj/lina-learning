"""Full-Power Canvas contracts kept outside generated visual implementation code.

This module deliberately owns the small common boundary shared by typed and
custom Canvas runtimes: reusable-artifact metadata, semantic manifests, and
the only event shape a custom sandbox may request.  It contains no Tutor,
student-record, browser, or Studio-write authority.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from functools import lru_cache
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.platform.db.models import VisualArtifact, VisualArtifactVersion


CANVAS_SEMANTIC_MANIFEST_VERSION = "canvas-semantic-manifest-v1"
CANVAS_SEMANTIC_EVENT_VERSION = "canvas-semantic-event-v1"
CUSTOM_VISUAL_PACKAGE_VERSION = "custom-visual-package-v1"
CUSTOM_VISUAL_RUNTIME_KIND = "custom-visual"

_SEMANTIC_ID = r"^[a-z][a-z0-9_-]*$"
_SAFE_DEPENDENCIES = frozenset({"native-svg-v1", "motion-v1"})
_FORBIDDEN_SOURCE_PATTERNS = (
    (r"\bfetch\s*\(", "fetch"), (r"\bXMLHttpRequest\b", "xmlhttprequest"), (r"\bWebSocket\b", "websocket"), (r"\bEventSource\b", "eventsource"),
    (r"\bdocument\.cookie\b", "cookie"), (r"\blocalStorage\b", "localstorage"), (r"\bsessionStorage\b", "sessionstorage"), (r"\bindexedDB\b", "indexeddb"),
    (r"\bwindow\.parent\b", "window.parent"), (r"\bwindow\.top\b", "window.top"), (r"\bimport\s*(?:\(|[^\w])", "import"),
    (r"\brequire\s*\(", "require"), (r"\beval\s*\(", "eval"), (r"\bFunction\s*\(", "function"), (r"\bnew\s+Worker\b", "worker"),
    (r"\bserviceWorker\b", "serviceworker"), (r"\bwindow\.open\s*\(", "window.open"), (r"\blocation\s*=", "location"),
)
_PRIVATE_MARKERS = ("student_id", "student id", "personal_memory", "learning_intelligence", "private", "cookie", "storage_key", "source_asset")


class CustomVisualSecurityError(ValueError):
    """Generated source requested an authority unavailable to visual packages."""


class CustomVisualSyntaxError(CustomVisualSecurityError):
    """Bounded parser location/category, without source excerpts or host paths."""

    def __init__(self, diagnostic: dict[str, int | str | None]):
        self.diagnostic = diagnostic
        super().__init__("CUSTOM_VISUAL_JAVASCRIPT_SYNTAX_INVALID")


class CustomVisualInteractionLayoutError(ValueError):
    """A declared learner interaction is present but cannot be laid out as usable UI."""


class VisualArtifactPrivacyError(ValueError):
    """A reusable definition attempted to retain student-private material."""


class SemanticBridgeError(ValueError):
    """A sandbox message does not match the declared educational contract."""


class CanvasSemanticEntityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    semantic_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    kind: str = Field(min_length=1, max_length=64)
    label: str = Field(min_length=1, max_length=160)
    educational_meaning: str = Field(min_length=1, max_length=500)
    visible_description: str = Field(min_length=1, max_length=320)


class CanvasSemanticRelationV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    relation: str = Field(min_length=1, max_length=64)
    target_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    meaning: str = Field(min_length=1, max_length=500)


class CanvasSemanticQuantityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    semantic_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    value: str = Field(min_length=1, max_length=120)
    unit: str | None = Field(default=None, max_length=80)
    provenance: str = Field(min_length=1, max_length=120)


class CanvasPresentationStepV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    semantic_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    label: str = Field(min_length=1, max_length=160)
    order: int = Field(ge=1, le=32)


class CanvasSemanticInteractionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    semantic_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    action: Literal["FOCUS", "SELECT", "MOVE", "SET_VALUE", "CONNECT", "SUBMIT", "REORDER", "TOGGLE", "STEP", "RESET_VIEW"]
    meaning: str = Field(min_length=1, max_length=400)
    value_required: bool = Field(default=False, description="False for SELECT and FOCUS, which cannot mutate values; true when a mutation requires a value.")

    @model_validator(mode="after")
    def action_value_contract(self):
        if self.action in {"SELECT", "FOCUS"} and self.value_required:
            raise ValueError("SELECT and FOCUS cannot require semantic values; set value_required false.")
        return self


class CanvasSemanticManifestV1(BaseModel):
    """Rendering-independent contract enabling same-Tutor Canvas continuity."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: Literal[CANVAS_SEMANTIC_MANIFEST_VERSION]
    brief_digest: str = Field(min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$")
    objective: str = Field(min_length=1, max_length=500)
    representation_summary: str = Field(min_length=1, max_length=600)
    entities: list[CanvasSemanticEntityV1] = Field(default_factory=list, max_length=48)
    relations: list[CanvasSemanticRelationV1] = Field(default_factory=list, max_length=96)
    quantities: list[CanvasSemanticQuantityV1] = Field(default_factory=list, max_length=48)
    presentation_steps: list[CanvasPresentationStepV1] = Field(default_factory=list, max_length=32)
    interactions: list[CanvasSemanticInteractionV1] = Field(default_factory=list, max_length=32)
    calculated_results: list[CanvasSemanticQuantityV1] = Field(default_factory=list, max_length=32)
    visual_descriptions: list[str] = Field(default_factory=list, max_length=24)
    current_state_schema: dict[str, str] = Field(default_factory=dict, max_length=24)
    provenance: dict[str, str] = Field(default_factory=dict, max_length=12)

    @model_validator(mode="after")
    def valid_semantic_references(self) -> "CanvasSemanticManifestV1":
        entity_ids = [entity.semantic_id for entity in self.entities]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("Semantic Manifest entity identifiers must be unique")
        known = set(entity_ids)
        if any(item.source_id not in known or item.target_id not in known for item in self.relations):
            raise ValueError("Semantic Manifest relations must reference declared entities")
        if any(item.semantic_id not in known for item in [*self.quantities, *self.calculated_results, *self.interactions]):
            raise ValueError("Semantic Manifest quantities and interactions must reference declared entities")
        if len({step.order for step in self.presentation_steps}) != len(self.presentation_steps):
            raise ValueError("Semantic Manifest presentation step order must be unique")
        return self


class CanvasSemanticManifestDraftV1(BaseModel):
    """Model-authored semantics before the application binds brief provenance."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: Literal[CANVAS_SEMANTIC_MANIFEST_VERSION] = CANVAS_SEMANTIC_MANIFEST_VERSION
    objective: str = Field(min_length=1, max_length=500)
    representation_summary: str = Field(min_length=1, max_length=600)
    entities: list[CanvasSemanticEntityV1] = Field(default_factory=list, max_length=48)
    relations: list[CanvasSemanticRelationV1] = Field(default_factory=list, max_length=96)
    quantities: list[CanvasSemanticQuantityV1] = Field(default_factory=list, max_length=48)
    presentation_steps: list[CanvasPresentationStepV1] = Field(default_factory=list, max_length=32)
    interactions: list[CanvasSemanticInteractionV1] = Field(default_factory=list, max_length=32)
    calculated_results: list[CanvasSemanticQuantityV1] = Field(default_factory=list, max_length=32)
    visual_descriptions: list[str] = Field(default_factory=list, max_length=24)
    current_state_schema: dict[str, str] = Field(default_factory=dict, max_length=24)
    provenance: dict[str, str] = Field(default_factory=dict, max_length=12)

    def bind_brief_digest(self, brief_digest: str) -> CanvasSemanticManifestV1:
        """Produce the immutable final contract from trusted run-local provenance."""
        payload = self.model_dump(mode="json")
        provenance = dict(payload.get("provenance", {}))
        provenance["brief_digest"] = brief_digest
        payload.update(brief_digest=brief_digest, provenance=provenance)
        return CanvasSemanticManifestV1.model_validate(payload)


def validate_visual_parameters(schema: dict[str, Any], parameters: dict[str, Any]) -> None:
    """Validate the supported scalar parameter contract at every binding boundary."""
    properties = schema.get("properties", {})
    if schema.get("type", "object") != "object" or not isinstance(properties, dict):
        raise ValueError("Invalid visual parameter schema.")
    if len(parameters) > 32 or not set(parameters) <= set(properties) or not set(schema.get("required", [])) <= set(parameters):
        raise ValueError("Visual parameter names do not match the implementation contract.")
    for key, value in parameters.items():
        rule = properties[key]
        kind = rule.get("type") if isinstance(rule, dict) else None
        valid = ((kind == "string" and isinstance(value, str) and len(value) <= 240)
                 or (kind == "boolean" and type(value) is bool)
                 or (kind == "integer" and type(value) is int)
                 or (kind == "number" and type(value) in (int, float) and math.isfinite(value)))
        if not valid or ("enum" in rule and value not in rule["enum"]):
            raise ValueError("Visual parameter value does not match its declared scalar type.")


@lru_cache(maxsize=128)
def _validate_javascript_syntax(source: str) -> None:
    """Parse only: never execute generated source or include it in diagnostics."""
    node = shutil.which("node")
    if node is None:
        raise CustomVisualSecurityError("CUSTOM_VISUAL_SYNTAX_VALIDATOR_UNAVAILABLE")
    try:
        result = subprocess.run([node, "--check", "-"], input=source, text=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=3)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CustomVisualSecurityError("CUSTOM_VISUAL_SYNTAX_VALIDATOR_UNAVAILABLE") from error
    if result.returncode:
        # Node's stderr includes source and a stack. Export only a numeric
        # location and an allowlisted category; never pass raw stderr onward.
        diagnostic = result.stderr or ""
        location = re.search(r"(?m)^\[stdin\]:(\d+)\s*$", diagnostic)
        caret = re.search(r"(?m)^([ \t]*)\^+\s*$", diagnostic)
        categories = ("Unexpected token", "Unexpected identifier", "Unexpected end of input",
                      "Invalid or unexpected token", "missing ) after argument list")
        category = next((value for value in categories if f"SyntaxError: {value}" in diagnostic), "Invalid JavaScript syntax")
        raise CustomVisualSyntaxError({"line": int(location[1]) if location else None,
            "column": len(caret[1]) + 1 if caret else None, "category": category})


class CustomVisualPackageV1(BaseModel):
    """A bounded executable package admitted only to the opaque iframe runtime."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: Literal[CUSTOM_VISUAL_PACKAGE_VERSION]
    runtime_kind: Literal[CUSTOM_VISUAL_RUNTIME_KIND]
    dependencies: list[str] = Field(min_length=1, max_length=4)
    source: str = Field(min_length=1, max_length=48_000)
    manifest: CanvasSemanticManifestV1
    parameter_schema: dict[str, Any] = Field(default_factory=dict, max_length=64)

    @model_validator(mode="after")
    def safe_package(self) -> "CustomVisualPackageV1":
        if not set(self.dependencies) <= _SAFE_DEPENDENCIES:
            raise CustomVisualSecurityError("Custom visual dependency is outside the approved allowlist")
        if len(self.dependencies) != len(set(self.dependencies)):
            raise CustomVisualSecurityError("Custom visual dependencies must be unique")
        for pattern, capability in _FORBIDDEN_SOURCE_PATTERNS:
            if re.search(pattern, self.source):
                raise CustomVisualSecurityError(f"CUSTOM_VISUAL_FORBIDDEN_API:{capability}")
        if "window.mount" not in self.source:
            raise CustomVisualSecurityError("Custom visual source must define window.mount")
        declared_interactions = {(item.action, item.semantic_id) for item in self.manifest.interactions}
        # Catch statically known mismatches. Shared handlers can compute a
        # declared target dynamically; string-literal matching is not a JS
        # security boundary. Every emitted pair is checked by both the browser
        # bridge and the server-owned Manifest resolver before Studio accepts it.
        for call in re.finditer(r"bridge\s*\.\s*emit\s*\(\s*", self.source):
            tail = self.source[call.end():]
            direct = re.match(r"['\"]([A-Z_]+)['\"]\s*,\s*['\"]([a-z][a-z0-9_-]*)['\"]\s*(?:,|\))", tail)
            if direct:
                pair = direct.groups()
                if pair not in declared_interactions:
                    raise CustomVisualSecurityError(f"SEMANTIC_INTERACTION_BINDING_INVALID: {pair[0]}:{pair[1]} is not declared; declared={sorted(declared_interactions)[:24]}")
            else:
                event = re.match(r"\{([^{}]*)", tail)
                action = re.search(r"\baction\s*:\s*['\"]([A-Z_]+)['\"]\s*(?:,|$)", event[1]) if event else None
                target = re.search(r"\bsemantic_id\s*:\s*['\"]([a-z][a-z0-9_-]*)['\"]\s*(?:,|$)", event[1]) if event else None
                if action and target and (action[1], target[1]) not in declared_interactions:
                    raise CustomVisualSecurityError("SEMANTIC_INTERACTION_BINDING_INVALID: static object event is not declared by the Manifest")
        # A HTML control appended below an SVG parent has no reliable layout or
        # accessibility box in the opaque document.  This exact error is
        # repairable by the model: mount controls in an HTML container, or use
        # SVG-native controls with pointer/keyboard handling.
        if (
            re.search(r"document\.createElement\(\s*['\"]button['\"]\s*\)", self.source, re.IGNORECASE)
            and re.search(r"\.parentNode\.appendChild\(\s*\w+\s*\)", self.source, re.IGNORECASE)
        ):
            raise CustomVisualInteractionLayoutError(
                "CUSTOM_VISUAL_INTERACTION_CONTROL_NOT_RENDERABLE: mount declared controls in an HTML container, not an SVG parent"
            )
        if not isinstance(self.parameter_schema.get("type", "object"), str):
            raise CustomVisualSecurityError("Custom visual parameter schema must be a JSON-schema object")
        _validate_javascript_syntax(self.source)
        return self


class CanvasSemanticEventV1(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: Literal[CANVAS_SEMANTIC_EVENT_VERSION]
    artifact_instance_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    nonce: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    semantic_action: Literal["FOCUS", "SELECT", "MOVE", "SET_VALUE", "CONNECT", "SUBMIT", "REORDER", "TOGGLE", "STEP", "RESET_VIEW"]
    semantic_id: str = Field(min_length=1, max_length=64, pattern=_SEMANTIC_ID)
    related_semantic_id: str | None = Field(default=None, max_length=64, pattern=_SEMANTIC_ID)
    from_value: str | None = Field(default=None, max_length=240)
    to_value: str | None = Field(default=None, max_length=240)
    step_id: str | None = Field(default=None, max_length=64, pattern=_SEMANTIC_ID)
    idempotency_key: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")


class CanvasSemanticBridge:
    """Validates the sole sandbox-to-Studio communication shape before settlement."""

    def __init__(self, *, manifest: CanvasSemanticManifestV1 | dict[str, object], artifact_instance_id: str, nonce: str) -> None:
        self.manifest = CanvasSemanticManifestV1.model_validate(manifest)
        self.artifact_instance_id = artifact_instance_id
        self.nonce = nonce

    def validate(self, payload: dict[str, object]) -> CanvasSemanticEventV1:
        event = CanvasSemanticEventV1.model_validate(payload)
        if event.artifact_instance_id != self.artifact_instance_id or event.nonce != self.nonce:
            raise SemanticBridgeError("Sandbox event identity does not match this visual instance")
        declared = next((item for item in self.manifest.interactions if item.semantic_id == event.semantic_id and item.action == event.semantic_action), None)
        if declared is None:
            raise SemanticBridgeError("Sandbox event action is not declared by the Semantic Manifest")
        if declared.value_required and event.to_value is None:
            raise SemanticBridgeError("Sandbox event requires a semantic value")
        known = {entity.semantic_id for entity in self.manifest.entities}
        if event.related_semantic_id is not None and event.related_semantic_id not in known:
            raise SemanticBridgeError("Sandbox event references an unknown related semantic entity")
        return event


@dataclass(frozen=True, slots=True)
class ReusableVisualArtifactVersion:
    artifact_id: str
    version_id: str
    stable_slug: str
    version_number: int
    semantic_purpose: str
    runtime_kind: str
    parameter_schema: dict[str, Any]
    manifest_contract: dict[str, Any]
    definition: dict[str, Any]
    lifecycle_status: Literal["CANDIDATE", "VALIDATED", "TRUSTED", "RETIRED"]
    source_digest: str
    parent_version_id: str | None = None


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _reject_private(value: object) -> None:
    content = _canonical(value).lower()
    if any(marker in content for marker in _PRIVATE_MARKERS):
        raise VisualArtifactPrivacyError("Reusable artifact definition contains student-private or authority-bearing material")


@dataclass
class ReusableVisualArtifactService:
    """Small project-owned registry core; persistence adapters may mirror these immutable values."""

    _versions: dict[str, ReusableVisualArtifactVersion] = field(default_factory=dict)

    def create_candidate(self, *, stable_slug: str, semantic_purpose: str, runtime_kind: str, parameter_schema: dict[str, Any], manifest_contract: dict[str, Any], definition: dict[str, Any], parent_version_id: str | None = None) -> ReusableVisualArtifactVersion:
        if re.fullmatch(_SEMANTIC_ID, stable_slug) is None:
            raise ValueError("Reusable artifact slug must be a stable semantic identifier")
        _reject_private(definition)
        _reject_private(manifest_contract)
        CanvasSemanticManifestV1.model_validate(manifest_contract)
        artifact_id = next((version.artifact_id for version in self._versions.values() if version.stable_slug == stable_slug), f"artifact-{uuid4().hex[:20]}")
        siblings = [version for version in self._versions.values() if version.artifact_id == artifact_id]
        value = ReusableVisualArtifactVersion(
            artifact_id=artifact_id,
            version_id=f"artifact-version-{uuid4().hex[:20]}",
            stable_slug=stable_slug,
            version_number=len(siblings) + 1,
            semantic_purpose=semantic_purpose,
            runtime_kind=runtime_kind,
            parameter_schema=json.loads(_canonical(parameter_schema)),
            manifest_contract=json.loads(_canonical(manifest_contract)),
            definition=json.loads(_canonical(definition)),
            lifecycle_status="CANDIDATE",
            source_digest=sha256(_canonical(definition).encode()).hexdigest(),
            parent_version_id=parent_version_id,
        )
        self._versions[value.version_id] = value
        return value

    def search(self, query: str, *, limit: int = 5) -> tuple[ReusableVisualArtifactVersion, ...]:
        words = set(query.lower().split())
        ranked = sorted(
            (value for value in self._versions.values() if value.lifecycle_status != "RETIRED"),
            key=lambda value: (len(words & set((value.semantic_purpose + " " + value.stable_slug).lower().replace("-", " ").split())), value.version_number),
            reverse=True,
        )
        return tuple(ranked[:max(1, min(limit, 5))])

    def adapt(self, version_id: str, *, parameters: dict[str, object]) -> dict[str, object]:
        version = self._versions[version_id]
        properties = version.parameter_schema.get("properties", {})
        if not isinstance(properties, dict) or not set(parameters) <= set(properties):
            raise ValueError("Artifact instance parameters are outside the declared schema")
        return {"artifact_version_id": version.version_id, "parameters": json.loads(_canonical(parameters))}


class PostgresVisualArtifactService:
    """Durable registry adapter.  Build history is intentionally stored elsewhere."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_candidate(self, *, stable_slug: str, semantic_purpose: str, runtime_kind: str, parameter_schema: dict[str, Any], manifest_contract: dict[str, Any], definition: dict[str, Any], dependency_capabilities: list[str] | None = None, parent_version_id=None) -> VisualArtifactVersion:
        if re.fullmatch(_SEMANTIC_ID, stable_slug) is None:
            raise ValueError("Reusable artifact slug must be a stable semantic identifier")
        _reject_private(definition)
        _reject_private(manifest_contract)
        CanvasSemanticManifestV1.model_validate(manifest_contract)
        artifact = self.session.scalar(select(VisualArtifact).where(VisualArtifact.stable_slug == stable_slug).with_for_update())
        if artifact is None:
            artifact = VisualArtifact(stable_slug=stable_slug, semantic_purpose=semantic_purpose, runtime_kind=runtime_kind, lifecycle_status="CANDIDATE")
            self.session.add(artifact)
            self.session.flush()
        next_version = int(self.session.scalar(select(func.coalesce(func.max(VisualArtifactVersion.version_number), 0)).where(VisualArtifactVersion.artifact_id == artifact.id)) or 0) + 1
        version = VisualArtifactVersion(
            artifact_id=artifact.id,
            parent_version_id=parent_version_id,
            version_number=next_version,
            source_digest=sha256(_canonical(definition).encode()).hexdigest(),
            runtime_contract_version=CUSTOM_VISUAL_PACKAGE_VERSION if runtime_kind == CUSTOM_VISUAL_RUNTIME_KIND else "typed-agentic-canvas-v1",
            parameter_schema=json.loads(_canonical(parameter_schema)),
            manifest_contract=json.loads(_canonical(manifest_contract)),
            dependency_capabilities=list(dependency_capabilities or []),
            definition_payload=json.loads(_canonical(definition)),
            validation_status="CANDIDATE",
        )
        self.session.add(version)
        self.session.flush()
        return version

    def search(self, query: str, *, limit: int = 5) -> list[VisualArtifactVersion]:
        words = [word for word in query.lower().split() if word]
        statement = (
            select(VisualArtifactVersion)
            .join(VisualArtifact, VisualArtifact.id == VisualArtifactVersion.artifact_id)
            .where(VisualArtifact.lifecycle_status != "RETIRED")
            .order_by(VisualArtifactVersion.created_at.desc())
            .limit(max(1, min(limit, 5)))
        )
        candidates = list(self.session.scalars(statement))
        return sorted(candidates, key=lambda item: sum(word in item.definition_payload.get("tags", []) or word in item.manifest_contract.get("representation_summary", "").lower() for word in words), reverse=True)
