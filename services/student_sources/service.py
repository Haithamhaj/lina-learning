"""Persistence and private-byte access for Student source assets."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import LearningMessage, LearningSession, StudentSourceAsset
from services.platform.storage import ObjectStorage, StorageIntegrityError

from .validation import ValidatedStudentSource


def store_source_asset(
    session: Session,
    *,
    storage: ObjectStorage,
    student_id: UUID,
    learning_session: LearningSession,
    source_message: LearningMessage,
    source: ValidatedStudentSource,
) -> StudentSourceAsset:
    """Store one immutable original and stage its DB lineage in the caller transaction."""

    if learning_session.student_id != student_id or source_message.session_id != learning_session.id:
        raise ValueError("Student source ownership does not match its message and session.")
    if source_message.role != "student" or source_message.source_asset_id is not None:
        raise ValueError("Student source message is unavailable for attachment.")
    asset_id = uuid4()
    storage_key = (
        f"student-sources/{student_id}/{learning_session.id}/{asset_id}/original"
    )
    stored = storage.put(
        storage_key,
        source.content,
        content_type=source.content_type,
        metadata={
            "student_id": str(student_id),
            "learning_session_id": str(learning_session.id),
            "source_asset_id": str(asset_id),
        },
    )
    try:
        if (
            stored.size != source.size
            or stored.checksum_sha256 != source.checksum_sha256
            or stored.content_type != source.content_type
        ):
            raise StorageIntegrityError("Stored Student source metadata does not match the validated original.")
        asset = StudentSourceAsset(
            id=asset_id,
            student_id=student_id,
            learning_session_id=learning_session.id,
            source_message_id=source_message.id,
            kind=source.kind,
            original_filename=source.filename,
            content_type=source.content_type,
            size_bytes=source.size,
            checksum_sha256=source.checksum_sha256,
            storage_key=storage_key,
        )
        session.add(asset)
        # Insert the immutable asset first. LearningMessage and StudentSourceAsset
        # intentionally point at each other, so relying on SQLAlchemy's default
        # flush ordering would update the message before the asset exists.
        session.flush([asset])
        source_message.source_asset_id = asset.id
        session.flush([source_message])
        return asset
    except Exception:
        storage.delete(storage_key)
        raise


def link_source_to_message(message: LearningMessage, *, asset: StudentSourceAsset) -> None:
    """Link an owned, already-persisted source to one later Student follow-up."""

    if message.role != "student" or message.session_id != asset.learning_session_id:
        raise ValueError("Student source cannot be linked outside its learning session.")
    if message.source_asset_id not in {None, asset.id}:
        raise ValueError("Student message already references another source.")
    message.source_asset_id = asset.id


def owned_source_asset(
    session: Session,
    *,
    student_id: UUID,
    learning_session_id: UUID,
    asset_id: UUID,
) -> StudentSourceAsset | None:
    """Resolve one opaque asset only inside its exact Student/session boundary."""

    return session.execute(
        select(StudentSourceAsset).where(
            StudentSourceAsset.id == asset_id,
            StudentSourceAsset.student_id == student_id,
            StudentSourceAsset.learning_session_id == learning_session_id,
        )
    ).scalar_one_or_none()


def provider_source_input(
    *, storage: ObjectStorage, asset: StudentSourceAsset
) -> dict[str, object]:
    """Load verified private bytes transiently for the current Tutor call only."""

    stored = storage.get(asset.storage_key)
    if (
        stored.metadata.size != asset.size_bytes
        or stored.metadata.checksum_sha256 != asset.checksum_sha256
        or stored.metadata.content_type != asset.content_type
    ):
        raise StorageIntegrityError("Student source storage no longer matches durable lineage.")
    return {
        "kind": asset.kind,
        "filename": asset.original_filename,
        "content_type": asset.content_type,
        "content": stored.content,
    }
