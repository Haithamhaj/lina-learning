"""Read-only, Parent-safe status projection for versioned content processing."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.platform.db.models import (
    ContentDocument,
    ContentIndexRun,
    ContentProcessingRun,
    ContentSemanticProcessingRun,
)


ReadinessStatus = Literal["UPLOADED", "PROCESSING", "READY", "FAILED"]
StageStatus = Literal["PENDING", "PROCESSING", "READY", "FAILED"]


class ContentStages(BaseModel):
    structural: StageStatus
    semantic: StageStatus
    index: StageStatus


class ContentFailure(BaseModel):
    stage: Literal["structural", "semantic", "index"]
    reason_code: str
    short_message: str


class ParentContentDocumentStatus(BaseModel):
    id: UUID
    filename: str
    grade_level: int
    subject: str
    upload_status: Literal["UPLOADED"]
    status: ReadinessStatus
    stages: ContentStages
    failure: ContentFailure | None


class ParentContentStatus(BaseModel):
    student_id: UUID
    documents: list[ParentContentDocumentStatus]


def parent_content_status_for_student(
    session: Session, *, student_id: UUID
) -> ParentContentStatus:
    """Return current pipeline readiness without creating or modifying any rows."""

    documents = session.execute(
        select(ContentDocument)
        .where(ContentDocument.student_id == student_id)
        .order_by(
            ContentDocument.grade_level,
            ContentDocument.subject,
            ContentDocument.filename,
            ContentDocument.created_at,
            ContentDocument.id,
        )
    ).scalars()
    return ParentContentStatus(
        student_id=student_id,
        documents=[_status_for_document(session, document=document) for document in documents],
    )


def _status_for_document(
    session: Session, *, document: ContentDocument
) -> ParentContentDocumentStatus:
    structural = _latest_structural_run(session, document_id=document.id)
    structural_status = _stage_status(structural)
    if structural_status == "FAILED":
        return _document_status(
            document, structural_status, "PENDING", "PENDING", _failure("structural")
        )
    if structural_status != "READY":
        status: ReadinessStatus = "UPLOADED" if structural is None else "PROCESSING"
        return _document_status(document, structural_status, "PENDING", "PENDING", None, status)

    semantic = _latest_semantic_run(session, document_id=document.id, structural_run_id=structural.id)
    semantic_status = _stage_status(semantic)
    if semantic_status == "FAILED":
        return _document_status(
            document, structural_status, semantic_status, "PENDING", _failure("semantic")
        )
    if semantic_status != "READY":
        return _document_status(document, structural_status, semantic_status, "PENDING", None)

    index = _latest_index_run(session, document_id=document.id, semantic_run_id=semantic.id)
    index_status = _stage_status(index)
    if index_status == "FAILED":
        return _document_status(
            document, structural_status, semantic_status, index_status, _failure("index")
        )
    return _document_status(
        document,
        structural_status,
        semantic_status,
        index_status,
        None,
        "READY" if index_status == "READY" else "PROCESSING",
    )


def _document_status(
    document: ContentDocument,
    structural: StageStatus,
    semantic: StageStatus,
    index: StageStatus,
    failure: ContentFailure | None,
    status: ReadinessStatus | None = None,
) -> ParentContentDocumentStatus:
    return ParentContentDocumentStatus(
        id=document.id,
        filename=document.filename,
        grade_level=document.grade_level,
        subject=document.subject,
        upload_status="UPLOADED",
        status=status or ("FAILED" if failure is not None else "PROCESSING"),
        stages=ContentStages(structural=structural, semantic=semantic, index=index),
        failure=failure,
    )


def _latest_structural_run(session: Session, *, document_id: UUID) -> ContentProcessingRun | None:
    return session.execute(
        select(ContentProcessingRun)
        .where(
            ContentProcessingRun.document_id == document_id,
            ContentProcessingRun.kind == "STRUCTURAL",
        )
        .order_by(ContentProcessingRun.created_at.desc(), ContentProcessingRun.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _latest_semantic_run(
    session: Session, *, document_id: UUID, structural_run_id: UUID
) -> ContentSemanticProcessingRun | None:
    return session.execute(
        select(ContentSemanticProcessingRun)
        .where(
            ContentSemanticProcessingRun.document_id == document_id,
            ContentSemanticProcessingRun.structural_processing_run_id == structural_run_id,
        )
        .order_by(
            ContentSemanticProcessingRun.created_at.desc(),
            ContentSemanticProcessingRun.id.desc(),
        )
        .limit(1)
    ).scalar_one_or_none()


def _latest_index_run(
    session: Session, *, document_id: UUID, semantic_run_id: UUID
) -> ContentIndexRun | None:
    return session.execute(
        select(ContentIndexRun)
        .where(
            ContentIndexRun.document_id == document_id,
            ContentIndexRun.semantic_processing_run_id == semantic_run_id,
        )
        .order_by(ContentIndexRun.created_at.desc(), ContentIndexRun.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _stage_status(run: object | None) -> StageStatus:
    if run is None:
        return "PENDING"
    raw_status = str(getattr(run, "status", "PENDING")).upper()
    if raw_status == "COMPLETED":
        return "READY"
    if raw_status == "FAILED":
        return "FAILED"
    return "PROCESSING"


def _failure(stage: Literal["structural", "semantic", "index"]) -> ContentFailure:
    messages = {
        "structural": ("STRUCTURAL_PROCESSING_FAILED", "Structural parsing could not be completed."),
        "semantic": ("SEMANTIC_PROCESSING_FAILED", "Semantic extraction could not be completed."),
        "index": ("INDEX_PROCESSING_FAILED", "Retrieval indexing could not be completed."),
    }
    reason_code, short_message = messages[stage]
    return ContentFailure(stage=stage, reason_code=reason_code, short_message=short_message)
