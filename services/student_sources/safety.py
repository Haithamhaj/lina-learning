"""Transient Student-source inspection before the protected Tutor boundary."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Protocol
from uuid import UUID
from zipfile import BadZipFile, ZipFile

from PIL import Image, UnidentifiedImageError
import pypdfium2 as pdfium

from services.model_gateway.openai_moderation_provider import (
    ModerationImage,
    SourceModerationSignal,
)
from services.platform.safety import SafetyDecision, SafetyPolicyService
from services.student_sources.docx import extract_docx_text


_TEXT_CHUNK_CHARACTERS = 20_000
_IMAGES_PER_REQUEST = 8
_IMAGE_CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class SourceModerationProvider(Protocol):
    def inspect(
        self,
        *,
        text: str,
        images: tuple[ModerationImage, ...],
    ) -> SourceModerationSignal: ...


class SourceInspectionError(ValueError):
    """Raised when a source cannot be safely converted to transient inputs."""


@dataclass(frozen=True, slots=True)
class _TransientInspection:
    text: str
    images: tuple[ModerationImage, ...]


class StudentSourceSafetyService:
    """Inspect an owned original without creating another durable source copy."""

    def __init__(
        self,
        *,
        provider: SourceModerationProvider,
        policy: SafetyPolicyService,
    ) -> None:
        self._provider = provider
        self._policy = policy

    def evaluate(
        self,
        *,
        student_id: UUID,
        source_message_id: UUID,
        source_asset_id: UUID,
        student_text: str,
        source_input: dict[str, object],
    ) -> SafetyDecision:
        interaction_ref = f"message:{source_message_id};source:{source_asset_id}"
        try:
            inspection = _inspect_source(source_input)
            categories: set[str] = set()
            for text, images in _moderation_batches(student_text, inspection):
                signal = self._provider.inspect(text=text, images=images)
                categories.update(signal.true_categories)
        except Exception:
            # This is a protected boundary: unreadable inputs, transport errors,
            # and malformed provider responses all fail closed with no raw data
            # copied into the audit record.
            return self._policy.fail_source_inspection(
                student_id=student_id,
                interaction_ref=interaction_ref,
            )
        return self._policy.evaluate_source_signal(
            student_id=student_id,
            interaction_ref=interaction_ref,
            true_categories=frozenset(categories),
        )


def _inspect_source(source_input: dict[str, object]) -> _TransientInspection:
    kind = source_input.get("kind")
    content_type = source_input.get("content_type")
    content = source_input.get("content")
    if not isinstance(content, bytes) or not content:
        raise SourceInspectionError("Student source bytes are unavailable.")
    if kind == "IMAGE":
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise SourceInspectionError("Student source image type is unsupported.")
        return _TransientInspection(
            text="",
            images=(ModerationImage(content_type=content_type, content=content),),
        )
    if kind == "PDF" and content_type == "application/pdf":
        return _inspect_pdf(content)
    if (
        kind == "DOCUMENT"
        and content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        return _inspect_docx(content)
    raise SourceInspectionError("Student source kind is unsupported.")


def _inspect_pdf(content: bytes) -> _TransientInspection:
    texts: list[str] = []
    images: list[ModerationImage] = []
    try:
        document = pdfium.PdfDocument(content)
        try:
            if len(document) == 0:
                raise SourceInspectionError("PDF has no pages.")
            for index in range(len(document)):
                page = document[index]
                try:
                    text_page = page.get_textpage()
                    try:
                        extracted = text_page.get_text_range().strip()
                        if extracted:
                            texts.append(extracted)
                    finally:
                        text_page.close()
                    rendered = page.render(scale=1).to_pil()
                    output = BytesIO()
                    rendered.convert("RGB").save(output, format="PNG")
                    images.append(ModerationImage("image/png", output.getvalue()))
                finally:
                    page.close()
        finally:
            document.close()
    except SourceInspectionError:
        raise
    except Exception as error:
        raise SourceInspectionError("PDF inspection failed.") from error
    return _TransientInspection(text="\n".join(texts), images=tuple(images))


def _inspect_docx(content: bytes) -> _TransientInspection:
    images: list[ModerationImage] = []
    try:
        text = extract_docx_text(content)
        with ZipFile(BytesIO(content)) as archive:
            for filename in sorted(
                name for name in archive.namelist() if name.startswith("word/media/")
            ):
                image_bytes = archive.read(filename)
                try:
                    with Image.open(BytesIO(image_bytes)) as image:
                        image.verify()
                        image_format = image.format
                except (UnidentifiedImageError, OSError):
                    continue
                content_type = _IMAGE_CONTENT_TYPES.get(image_format or "")
                if content_type is not None:
                    images.append(ModerationImage(content_type, image_bytes))
    except (BadZipFile, KeyError, OSError) as error:
        raise SourceInspectionError("DOCX inspection failed.") from error
    if not text and not images:
        raise SourceInspectionError("DOCX contains no inspectable content.")
    return _TransientInspection(text=text, images=tuple(images))


def _moderation_batches(
    student_text: str,
    inspection: _TransientInspection,
) -> tuple[tuple[str, tuple[ModerationImage, ...]], ...]:
    combined_text = "\n".join(part for part in (student_text.strip(), inspection.text) if part)
    text_chunks = tuple(
        combined_text[index : index + _TEXT_CHUNK_CHARACTERS]
        for index in range(0, len(combined_text), _TEXT_CHUNK_CHARACTERS)
    )
    image_chunks = tuple(
        inspection.images[index : index + _IMAGES_PER_REQUEST]
        for index in range(0, len(inspection.images), _IMAGES_PER_REQUEST)
    )
    batch_count = max(len(text_chunks), len(image_chunks), 1)
    batches = tuple(
        (
            text_chunks[index] if index < len(text_chunks) else "",
            image_chunks[index] if index < len(image_chunks) else (),
        )
        for index in range(batch_count)
    )
    if any(text or images for text, images in batches):
        return batches
    raise SourceInspectionError("Student source inspection input is empty.")
