"""Owned persistence and resolution for immutable custom Canvas build packages."""
from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.platform.db.models import StudioCanvasSpecialistRun, VisualArtifact, VisualArtifactBuild, VisualArtifactVersion
from services.platform.storage import ObjectStorage, StorageIntegrityError, create_object_storage
from services.studio.full_power_canvas import CanvasSemanticManifestV1, CustomVisualPackageV1


class CustomVisualBuildResolutionError(ValueError):
    """A build is unavailable, outside its owner lineage, or fails integrity."""


@dataclass(frozen=True, slots=True)
class ResolvedCustomVisualBuild:
    build_id: UUID
    package: CustomVisualPackageV1
    manifest_digest: str


def persist_custom_visual_build(session: Session, *, storage: ObjectStorage, run: StudioCanvasSpecialistRun, package: CustomVisualPackageV1, parent_build_id: UUID | None = None, repair_kind: str | None = None) -> VisualArtifactBuild:
    """Store one validated package under a server-derived immutable key."""
    payload = json.dumps(package.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    digest = sha256(payload).hexdigest()
    build_id = uuid4()
    key = f"studio-custom-visual-builds/{run.student_id}/{run.learning_session_id}/{run.studio_runtime_id}/{build_id}/package.json"
    stored = storage.put(key, payload, content_type="application/json", metadata={"source_run_id": str(run.id), "visual_artifact_build_id": str(build_id), "checksum_sha256": digest})
    if stored.checksum_sha256 != digest or stored.size != len(payload):
        storage.delete(key)
        raise StorageIntegrityError("Stored custom visual package does not match validated output.")
    manifest = package.manifest.model_dump(mode="json")
    technical_metadata = {"runtime_kind": package.runtime_kind, "dependencies": list(package.dependencies), "source_run_id": str(run.id)}
    if parent_build_id is not None:
        technical_metadata["parent_build_id"] = str(parent_build_id)
    if repair_kind is not None:
        technical_metadata["repair_kind"] = repair_kind
    build = VisualArtifactBuild(id=build_id, artifact_version_id=None, source_digest=sha256(package.source.encode()).hexdigest(), bundle_digest=digest, package_storage_key=key, package_content_type="application/json", manifest_digest=sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(), manifest_metadata=manifest, status="VALIDATED", technical_metadata=technical_metadata)
    session.add(build)
    return build


def repair_custom_visual_source(
    session: Session,
    *,
    storage: ObjectStorage,
    run: StudioCanvasSpecialistRun,
    parent: ResolvedCustomVisualBuild,
    repaired_source: str,
) -> VisualArtifactBuild:
    """Persist one source-only revision while preserving the canonical Manifest."""
    package = parent.package.model_copy(update={"source": repaired_source})
    build = persist_custom_visual_build(
        session,
        storage=storage,
        run=run,
        package=package,
        parent_build_id=parent.build_id,
        repair_kind="SOURCE_ONLY_LAYOUT",
    )
    if build.manifest_digest != parent.manifest_digest:
        raise CustomVisualBuildResolutionError("Source-only repair changed the canonical Semantic Manifest.")
    return build


class CustomVisualBuildResolver:
    """The sole server-owned boundary for custom-build package and Manifest reads."""

    def __init__(self, storage: ObjectStorage | None = None) -> None:
        self._storage = storage or create_object_storage()

    def resolve(
        self,
        session: Session,
        *,
        build_id: UUID,
        student_id: UUID,
        runtime_id: UUID,
    ) -> ResolvedCustomVisualBuild:
        return resolve_custom_visual_build(
            session,
            storage=self._storage,
            build_id=build_id,
            student_id=student_id,
            runtime_id=runtime_id,
        )

    def resolve_artifact_version(self, session: Session, *, version_id: UUID, student_id: UUID, runtime_id: UUID) -> ResolvedCustomVisualBuild:
        version = session.get(VisualArtifactVersion, version_id)
        artifact = session.get(VisualArtifact, version.artifact_id) if version is not None else None
        if (
            version is None
            or artifact is None
            or artifact.lifecycle_status not in {"VALIDATED", "TRUSTED"}
            or version.validation_status not in {"VALIDATED", "TRUSTED"}
            or version.implementation_build_id is None
        ):
            raise CustomVisualBuildResolutionError("Reusable visual version is unavailable.")
        # A promoted version may be instantiated in a later runtime for the
        # same learner.  This narrow exception to direct-build runtime binding
        # is available only through a validated server-owned Version.
        build = session.get(VisualArtifactBuild, version.implementation_build_id)
        source_run_id = build.technical_metadata.get("source_run_id") if build is not None else None
        source_run = session.get(StudioCanvasSpecialistRun, source_run_id) if isinstance(source_run_id, str) else None
        if build is None or build.status != "VALIDATED" or source_run is None or source_run.student_id != student_id:
            raise CustomVisualBuildResolutionError("Reusable visual implementation is outside this learner ownership boundary.")
        return _resolve_build_payload(session, storage=self._storage, build=build)


def resolve_custom_visual_build(session: Session, *, storage: ObjectStorage, build_id: UUID, student_id: UUID, runtime_id: UUID, allow_source_layout_repair: bool = False) -> ResolvedCustomVisualBuild:
    build = session.get(VisualArtifactBuild, build_id)
    if build is None or build.status != "VALIDATED" or not build.package_storage_key:
        raise CustomVisualBuildResolutionError("Custom visual build is unavailable.")
    run_id = build.technical_metadata.get("source_run_id")
    run = session.get(StudioCanvasSpecialistRun, run_id) if isinstance(run_id, str) else None
    if run is None or run.student_id != student_id or run.studio_runtime_id != runtime_id:
        raise CustomVisualBuildResolutionError("Custom visual build is outside this Studio runtime.")
    return _resolve_build_payload(session, storage=storage, build=build, allow_source_layout_repair=allow_source_layout_repair)


def _resolve_build_payload(session: Session, *, storage: ObjectStorage, build: VisualArtifactBuild, allow_source_layout_repair: bool = False) -> ResolvedCustomVisualBuild:
    """Load bytes only after a caller has completed its ownership authorization."""
    if not build.package_storage_key:
        raise CustomVisualBuildResolutionError("Custom visual build package is unavailable.")
    stored = storage.get(build.package_storage_key)
    if (
        build.bundle_digest != stored.metadata.checksum_sha256
        or build.bundle_digest != sha256(stored.content).hexdigest()
    ):
        raise CustomVisualBuildResolutionError("Custom visual build digest is invalid.")
    try:
        package = CustomVisualPackageV1.model_validate_json(stored.content)
    except Exception as exc:
        if not allow_source_layout_repair or "CONTROL_NOT_RENDERABLE" not in str(exc):
            raise CustomVisualBuildResolutionError("Custom visual build package is invalid.") from exc
        raw = json.loads(stored.content)
        package = CustomVisualPackageV1.model_construct(
            version=raw["version"], runtime_kind=raw["runtime_kind"], dependencies=raw["dependencies"],
            source=raw["source"], manifest=CanvasSemanticManifestV1.model_validate(raw["manifest"]),
            parameter_schema=raw.get("parameter_schema", {}),
        )
    manifest_digest = sha256(json.dumps(
        package.manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()
    if build.manifest_digest != manifest_digest:
        raise CustomVisualBuildResolutionError("Custom visual Manifest digest is invalid.")
    return ResolvedCustomVisualBuild(
        build_id=build.id,
        package=package,
        manifest_digest=manifest_digest,
    )


def promote_custom_visual_build(
    session: Session,
    *,
    resolver: CustomVisualBuildResolver,
    build_id: UUID,
    student_id: UUID,
    runtime_id: UUID,
    stable_slug: str,
    semantic_purpose: str,
    parameter_schema: dict[str, object],
    promotion_reason: str,
) -> VisualArtifactVersion:
    """Promote one accepted Build without copying executable source to the registry."""
    if not stable_slug or not promotion_reason:
        raise ValueError("Reusable visual promotion requires a stable purpose and acceptance evidence.")
    resolved = resolver.resolve(session, build_id=build_id, student_id=student_id, runtime_id=runtime_id)
    package = resolved.package
    # Registry payload is descriptive metadata only; executable authority is
    # implementation_build_id and is always resolved server side.
    manifest = package.manifest.model_dump(mode="json")
    from services.studio.full_power_canvas import _reject_private
    _reject_private(manifest)
    artifact = session.scalar(select(VisualArtifact).where(VisualArtifact.stable_slug == stable_slug).with_for_update())
    if artifact is None:
        artifact = VisualArtifact(
            stable_slug=stable_slug,
            semantic_purpose=semantic_purpose,
            runtime_kind=package.runtime_kind,
            lifecycle_status="VALIDATED",
        )
        session.add(artifact)
        session.flush()
    if artifact.runtime_kind != package.runtime_kind:
        raise ValueError("Reusable visual promotion runtime kind is inconsistent.")
    number = int(session.scalar(select(func.coalesce(func.max(VisualArtifactVersion.version_number), 0)).where(VisualArtifactVersion.artifact_id == artifact.id)) or 0) + 1
    version = VisualArtifactVersion(
        artifact_id=artifact.id,
        parent_version_id=None,
        implementation_build_id=build_id,
        version_number=number,
        source_digest=build.source_digest,
        runtime_contract_version=package.version,
        parameter_schema=parameter_schema or package.parameter_schema,
        manifest_contract=manifest,
        dependency_capabilities=list(package.dependencies),
        definition_payload={"kind": "canonical-build-reference", "tags": [stable_slug, package.runtime_kind]},
        validation_status="VALIDATED",
        technical_evidence={"promotion_reason": promotion_reason, "implementation_build_id": str(build_id), "manifest_digest": resolved.manifest_digest},
    )
    session.add(version)
    session.flush()
    build = session.get(VisualArtifactBuild, build_id)
    assert build is not None
    build.artifact_version_id = version.id
    return version


def adapt_promoted_custom_visual_build(
    session: Session,
    *,
    resolver: CustomVisualBuildResolver,
    storage: ObjectStorage,
    parent_version_id: UUID,
    student_id: UUID,
    runtime_id: UUID,
    run: StudioCanvasSpecialistRun,
    package: CustomVisualPackageV1,
    generalized_change: str,
) -> VisualArtifactVersion:
    """Create a structural ADAPT child; ordinary instance parameters never enter here."""
    if not generalized_change.strip():
        raise ValueError("ADAPT requires a generalized structural change.")
    parent = session.get(VisualArtifactVersion, parent_version_id)
    if parent is None or parent.implementation_build_id is None:
        raise CustomVisualBuildResolutionError("ADAPT parent version is unavailable.")
    artifact = session.get(VisualArtifact, parent.artifact_id)
    if artifact is None or artifact.lifecycle_status not in {"VALIDATED", "TRUSTED"} or parent.validation_status not in {"VALIDATED", "TRUSTED"}:
        raise CustomVisualBuildResolutionError("ADAPT parent version is not trusted.")
    old = resolver.resolve_artifact_version(session, version_id=parent.id, student_id=student_id, runtime_id=runtime_id)
    if package.source == old.package.source:
        raise ValueError("ADAPT must change generalized implementation, not only instance parameters.")
    _reject_private(package.manifest.model_dump(mode="json"))
    build = persist_custom_visual_build(
        session,
        storage=storage,
        run=run,
        package=package,
        parent_build_id=old.build_id,
        repair_kind="ADAPT_GENERALIZED",
    )
    number = int(session.scalar(select(func.coalesce(func.max(VisualArtifactVersion.version_number), 0)).where(VisualArtifactVersion.artifact_id == parent.artifact_id)) or 0) + 1
    child = VisualArtifactVersion(
        artifact_id=parent.artifact_id,
        parent_version_id=parent.id,
        implementation_build_id=build.id,
        version_number=number,
        source_digest=build.source_digest,
        runtime_contract_version=package.version,
        parameter_schema=package.parameter_schema,
        manifest_contract=package.manifest.model_dump(mode="json"),
        dependency_capabilities=list(package.dependencies),
        definition_payload={"kind": "canonical-build-reference", "tags": list(parent.definition_payload.get("tags", []))},
        validation_status="VALIDATED",
        technical_evidence={
            "route": "ADAPT",
            "parent_version_id": str(parent.id),
            "generalized_change": generalized_change,
            "manifest_digest": build.manifest_digest,
            "implementation_build_id": str(build.id),
        },
    )
    session.add(child)
    session.flush()
    build.artifact_version_id = child.id
    return child
