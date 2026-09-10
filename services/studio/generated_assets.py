"""Owned persistence and resolution for derived Studio-generated images."""

from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from io import BytesIO
from uuid import UUID, uuid4

from PIL import Image, UnidentifiedImageError
from sqlalchemy import event, select
from sqlalchemy.orm import Session, SessionTransaction

from services.platform.db.models import StudioCanvasSpecialistRun, StudioGeneratedAsset
from services.platform.storage import (
    ObjectStorage,
    StorageError,
    StorageIntegrityError,
    StoredObject,
)
from services.studio.agentic_canvas import AgenticCanvasSceneV1

DEFAULT_MAX_GENERATED_IMAGE_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_GENERATED_IMAGE_PIXELS = 20_000_000
_IMAGE_MIME_BY_FORMAT = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
_TEMPORARY_HANDLE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,127}$")
_PENDING_COMPENSATIONS = "studio_generated_asset_pending_compensations"
_COMPENSATION_LISTENERS = "studio_generated_asset_compensation_listeners"
_OUTER_COMMIT_ATTEMPT = "studio_generated_asset_outer_commit_attempt"
_OUTER_COMMIT_SUCCEEDED = "studio_generated_asset_outer_commit_succeeded"


class GeneratedAssetValidationError(ValueError):
    """Raised before persistence when derived bytes or references are unsafe."""


@dataclass(frozen=True, slots=True)
class ValidatedGeneratedImage:
    content: bytes
    content_type: str
    size_bytes: int
    checksum_sha256: str


@dataclass(frozen=True, slots=True)
class GeneratedImageResolution:
    """Run-local bridge from one temporary hosted-tool handle to owned lineage."""

    temporary_handle: str
    asset: StudioGeneratedAsset

    @property
    def asset_id(self) -> UUID:
        return self.asset.id


def _delete_pending_objects(session: Session) -> None:
    pending = session.info.pop(_PENDING_COMPENSATIONS, {})
    first_error: StorageError | None = None
    for storage, storage_key in pending.values():
        try:
            storage.delete(storage_key)
        except StorageError as exc:  # cleanup must attempt every registered object
            first_error = first_error or exc
    if first_error is not None:
        raise first_error


def _before_session_commit(session: Session) -> None:
    # A savepoint commit is not durable ownership. Only mark an attempt when
    # Session.commit() is preparing the outer transaction.
    if not session.in_nested_transaction():
        session.info[_OUTER_COMMIT_ATTEMPT] = True
        session.info[_OUTER_COMMIT_SUCCEEDED] = False


def _after_session_commit(session: Session) -> None:
    if session.info.get(_OUTER_COMMIT_ATTEMPT):
        session.info[_OUTER_COMMIT_SUCCEEDED] = True


def _after_session_transaction_end(
    session: Session,
    transaction: SessionTransaction,
) -> None:
    if transaction.parent is not None:
        return
    try:
        if session.info.pop(_OUTER_COMMIT_SUCCEEDED, False):
            session.info.pop(_PENDING_COMPENSATIONS, None)
        else:
            _delete_pending_objects(session)
    finally:
        session.info.pop(_OUTER_COMMIT_ATTEMPT, None)


def _register_transaction_compensation(
    session: Session,
    *,
    storage: ObjectStorage,
    storage_key: str,
) -> None:
    pending = session.info.setdefault(_PENDING_COMPENSATIONS, {})
    pending[storage_key] = (storage, storage_key)
    if session.info.get(_COMPENSATION_LISTENERS):
        return
    event.listen(session, "before_commit", _before_session_commit)
    event.listen(session, "after_commit", _after_session_commit)
    event.listen(session, "after_transaction_end", _after_session_transaction_end)
    session.info[_COMPENSATION_LISTENERS] = True


def validate_generated_image_output(
    *,
    content: bytes,
    content_type: str,
    max_bytes: int = DEFAULT_MAX_GENERATED_IMAGE_BYTES,
    max_image_pixels: int = DEFAULT_MAX_GENERATED_IMAGE_PIXELS,
) -> ValidatedGeneratedImage:
    """Validate exact image bytes before the application adopts provider output."""

    normalized_content_type = content_type.split(";", 1)[0].strip().lower()
    if normalized_content_type not in _IMAGE_MIME_BY_FORMAT.values():
        raise GeneratedAssetValidationError("Generated output must be a supported image.")
    if not isinstance(content, bytes) or not content:
        raise GeneratedAssetValidationError("Generated output is an invalid image.")
    if len(content) > max_bytes:
        raise GeneratedAssetValidationError("Generated image exceeds the allowed size.")
    try:
        with Image.open(BytesIO(content)) as image:
            actual_content_type = _IMAGE_MIME_BY_FORMAT.get(image.format or "")
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise GeneratedAssetValidationError("Generated output is an invalid image.") from exc
    if actual_content_type != normalized_content_type:
        raise GeneratedAssetValidationError("Generated image content does not match its MIME.")
    if width <= 0 or height <= 0 or width * height > max_image_pixels:
        raise GeneratedAssetValidationError("Generated image exceeds the allowed pixel count.")
    return ValidatedGeneratedImage(
        content=content,
        content_type=normalized_content_type,
        size_bytes=len(content),
        checksum_sha256=hashlib.sha256(content).hexdigest(),
    )


def adopt_generated_image(
    session: Session,
    *,
    storage: ObjectStorage,
    run: StudioCanvasSpecialistRun,
    temporary_handle: str,
    content: bytes,
    content_type: str,
    max_bytes: int = DEFAULT_MAX_GENERATED_IMAGE_BYTES,
    max_image_pixels: int = DEFAULT_MAX_GENERATED_IMAGE_PIXELS,
) -> GeneratedImageResolution:
    """Copy validated bytes into owned storage and stage immutable DB lineage."""

    if not _TEMPORARY_HANDLE.fullmatch(temporary_handle):
        raise GeneratedAssetValidationError("Generated image handle is invalid.")
    if run.id is None or run.student_id is None or run.learning_session_id is None or run.studio_runtime_id is None:
        raise GeneratedAssetValidationError("Generated image run ownership is incomplete.")
    image = validate_generated_image_output(
        content=content,
        content_type=content_type,
        max_bytes=max_bytes,
        max_image_pixels=max_image_pixels,
    )
    asset_id = uuid4()
    storage_key = (
        f"studio-generated-assets/{run.student_id}/{run.learning_session_id}/"
        f"{run.studio_runtime_id}/{asset_id}/image"
    )
    stored = storage.put(
        storage_key,
        image.content,
        content_type=image.content_type,
        metadata={
            "student_id": str(run.student_id),
            "learning_session_id": str(run.learning_session_id),
            "studio_runtime_id": str(run.studio_runtime_id),
            "source_run_id": str(run.id),
            "studio_generated_asset_id": str(asset_id),
        },
    )
    try:
        if (
            stored.size != image.size_bytes
            or stored.checksum_sha256 != image.checksum_sha256
            or stored.content_type != image.content_type
        ):
            raise StorageIntegrityError("Stored generated image does not match validated output.")
        asset = StudioGeneratedAsset(
            id=asset_id,
            student_id=run.student_id,
            learning_session_id=run.learning_session_id,
            studio_runtime_id=run.studio_runtime_id,
            source_run_id=run.id,
            kind="IMAGE",
            content_type=image.content_type,
            size_bytes=image.size_bytes,
            checksum_sha256=image.checksum_sha256,
            storage_key=storage_key,
        )
        session.add(asset)
        session.flush([asset])
        if isinstance(session, Session):
            _register_transaction_compensation(
                session,
                storage=storage,
                storage_key=storage_key,
            )
        return GeneratedImageResolution(temporary_handle=temporary_handle, asset=asset)
    except Exception:
        storage.delete(storage_key)
        raise


def resolve_generated_image_handles(
    scene_payload: Mapping[str, object],
    *,
    resolutions: Sequence[GeneratedImageResolution],
) -> dict[str, object]:
    """Replace run-local image handles with owned opaque IDs before settlement."""

    resolved_by_handle: dict[str, StudioGeneratedAsset] = {}
    for resolution in resolutions:
        if resolution.temporary_handle in resolved_by_handle:
            raise GeneratedAssetValidationError("Generated image handle was resolved more than once.")
        resolved_by_handle[resolution.temporary_handle] = resolution.asset

    payload = copy.deepcopy(dict(scene_payload))
    blocks = payload.get("blocks")
    if not isinstance(blocks, list):
        raise GeneratedAssetValidationError("Generated Canvas scene blocks are invalid.")
    used_handles: set[str] = set()
    for block in blocks:
        if not isinstance(block, dict):
            raise GeneratedAssetValidationError("Generated Canvas scene block is invalid.")
        if block.get("type") != "IMAGE":
            continue
        handle = block.pop("temporary_image_handle", None)
        # A provider URL is transient transport metadata. It is discarded and
        # cannot enter the strict project-owned Scene contract.
        block.pop("provider_url", None)
        if not isinstance(handle, str) or handle not in resolved_by_handle:
            raise GeneratedAssetValidationError("Generated image handle is unresolved.")
        if handle in used_handles:
            raise GeneratedAssetValidationError("Generated image handle cannot be reused by multiple blocks.")
        used_handles.add(handle)
        block["studio_generated_asset_id"] = str(resolved_by_handle[handle].id)
    if used_handles != set(resolved_by_handle):
        raise GeneratedAssetValidationError("Generated image resolution is not referenced by the scene.")
    try:
        return AgenticCanvasSceneV1.model_validate(payload).model_dump(mode="json")
    except ValueError as exc:
        raise GeneratedAssetValidationError("Resolved generated image scene is invalid.") from exc


def owned_generated_asset(
    session: Session,
    *,
    student_id: UUID,
    runtime_id: UUID,
    asset_id: UUID,
) -> StudioGeneratedAsset | None:
    """Resolve one opaque generated asset inside its exact owner/runtime boundary."""

    return session.execute(
        select(StudioGeneratedAsset).where(
            StudioGeneratedAsset.id == asset_id,
            StudioGeneratedAsset.student_id == student_id,
            StudioGeneratedAsset.studio_runtime_id == runtime_id,
        )
    ).scalar_one_or_none()


def read_generated_asset(*, storage: ObjectStorage, asset: StudioGeneratedAsset) -> StoredObject:
    """Read private bytes only when storage still matches immutable DB lineage."""

    stored = storage.get(asset.storage_key)
    expected_metadata = {
        "student_id": str(asset.student_id),
        "learning_session_id": str(asset.learning_session_id),
        "studio_runtime_id": str(asset.studio_runtime_id),
        "source_run_id": str(asset.source_run_id),
        "studio_generated_asset_id": str(asset.id),
    }
    if (
        stored.metadata.size != asset.size_bytes
        or stored.metadata.checksum_sha256 != asset.checksum_sha256
        or stored.metadata.content_type != asset.content_type
        or any(stored.metadata.metadata.get(key) != value for key, value in expected_metadata.items())
    ):
        raise StorageIntegrityError("Generated Studio asset storage no longer matches durable lineage.")
    return stored
