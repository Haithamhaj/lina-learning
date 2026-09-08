"""Strict validation for one immutable Student source original."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from PIL import Image, UnidentifiedImageError
import pypdfium2


DEFAULT_MAX_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_IMAGE_PIXELS = 20_000_000
DEFAULT_MAX_PDF_PAGES = 25
_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_SUPPORTED = {
    ".jpg": ("IMAGE", "image/jpeg"),
    ".jpeg": ("IMAGE", "image/jpeg"),
    ".png": ("IMAGE", "image/png"),
    ".webp": ("IMAGE", "image/webp"),
    ".pdf": ("PDF", "application/pdf"),
    ".docx": ("DOCUMENT", _DOCX_MIME),
}
_IMAGE_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}


class StudentSourceValidationError(ValueError):
    """Raised before storage when source bytes do not meet the contract."""


@dataclass(frozen=True, slots=True)
class ValidatedStudentSource:
    kind: str
    filename: str
    content_type: str
    content: bytes
    size: int
    checksum_sha256: str


def validate_student_source(
    *,
    content: bytes,
    filename: str | None,
    content_type: str | None,
    max_bytes: int | None = None,
    max_document_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES,
    max_image_pixels: int = DEFAULT_MAX_IMAGE_PIXELS,
    max_pdf_pages: int = DEFAULT_MAX_PDF_PAGES,
) -> ValidatedStudentSource:
    """Validate type, structure and application bounds without changing bytes."""

    if not isinstance(content, bytes) or not content:
        raise StudentSourceValidationError("Student source is empty.")
    if not isinstance(filename, str) or not filename.strip():
        raise StudentSourceValidationError("Student source filename is required.")
    safe_filename = PurePath(filename).name
    if (
        safe_filename != filename
        or safe_filename in {".", ".."}
        or len(safe_filename) > 255
        or "\\" in safe_filename
        or any(ord(character) < 32 for character in safe_filename)
    ):
        raise StudentSourceValidationError("Student source filename is invalid.")
    extension = PurePath(safe_filename).suffix.lower()
    expected = _SUPPORTED.get(extension)
    if expected is None:
        raise StudentSourceValidationError("Student source type is unsupported.")
    kind, expected_mime = expected
    normalized_mime = (content_type or "").split(";", 1)[0].strip().lower()
    if normalized_mime != expected_mime:
        raise StudentSourceValidationError("Student source MIME does not match its filename.")
    application_max_bytes = max_bytes if max_bytes is not None else DEFAULT_MAX_BYTES
    effective_max_bytes = min(application_max_bytes, max_document_bytes) if kind == "DOCUMENT" else application_max_bytes
    if len(content) > effective_max_bytes:
        raise StudentSourceValidationError("Student source exceeds the allowed size.")

    if kind == "IMAGE":
        _validate_image(content, expected_mime, max_image_pixels=max_image_pixels)
    elif kind == "PDF":
        if not content.startswith(b"%PDF-"):
            raise StudentSourceValidationError("Student source content does not match its file type.")
        _validate_pdf(content, max_pdf_pages=max_pdf_pages)
    else:
        if not content.startswith(b"PK"):
            raise StudentSourceValidationError("Student source content does not match its file type.")
        _validate_docx(content)

    return ValidatedStudentSource(
        kind=kind,
        filename=safe_filename,
        content_type=expected_mime,
        content=content,
        size=len(content),
        checksum_sha256=hashlib.sha256(content).hexdigest(),
    )


def _validate_image(content: bytes, expected_mime: str, *, max_image_pixels: int) -> None:
    try:
        with Image.open(BytesIO(content)) as image:
            actual_mime = _IMAGE_FORMATS.get(image.format or "")
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise StudentSourceValidationError("Student source is an invalid image.") from exc
    if actual_mime != expected_mime:
        raise StudentSourceValidationError("Student source image content does not match its MIME.")
    if width <= 0 or height <= 0 or width * height > max_image_pixels:
        raise StudentSourceValidationError("Student source exceeds the allowed image pixels.")


def _validate_pdf(content: bytes, *, max_pdf_pages: int) -> None:
    if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-2048:]:
        raise StudentSourceValidationError("Student source is an invalid PDF.")
    document = None
    try:
        # Parse only enough structure to reject malformed/encrypted input and
        # enforce the interactive page bound. Semantic extraction remains in
        # the one primary Tutor provider call.
        document = pypdfium2.PdfDocument(content)
        page_count = len(document)
    except Exception as exc:
        raise StudentSourceValidationError("Student source is an invalid PDF.") from exc
    finally:
        if document is not None:
            document.close()
    if page_count <= 0:
        raise StudentSourceValidationError("Student source is an invalid PDF.")
    if page_count > max_pdf_pages:
        raise StudentSourceValidationError("Student source exceeds the allowed PDF pages.")


def _validate_docx(content: bytes) -> None:
    try:
        with ZipFile(BytesIO(content)) as archive:
            names = set(archive.namelist())
            if not {"[Content_Types].xml", "word/document.xml"}.issubset(names):
                raise StudentSourceValidationError("Student source is an invalid DOCX.")
            if sum(item.file_size for item in archive.infolist()) > 50 * 1024 * 1024:
                raise StudentSourceValidationError("Student source DOCX expands beyond the allowed size.")
            if archive.getinfo("word/document.xml").file_size > 5 * 1024 * 1024:
                raise StudentSourceValidationError("Student source DOCX text exceeds the allowed size.")
            ElementTree.fromstring(archive.read("word/document.xml"))
    except StudentSourceValidationError:
        raise
    except (BadZipFile, KeyError, OSError, RuntimeError, ElementTree.ParseError) as exc:
        raise StudentSourceValidationError("Student source is an invalid DOCX.") from exc
