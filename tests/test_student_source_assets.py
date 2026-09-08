from __future__ import annotations

import importlib
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from PIL import Image


def _validation_module():
    try:
        module = importlib.import_module("services.student_sources.validation")
    except ModuleNotFoundError:
        module = None
    assert module is not None
    return module


def _png(*, width: int = 2, height: int = 2) -> bytes:
    output = BytesIO()
    Image.new("RGB", (width, height), color="white").save(output, format="PNG")
    return output.getvalue()


def _docx() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Fractions</w:t></w:r></w:p></w:body></w:document>',
        )
    return output.getvalue()


def _pdf(*, pages: int = 1) -> bytes:
    output = BytesIO()
    images = [Image.new("RGB", (32, 32), "white") for _ in range(pages)]
    images[0].save(output, format="PDF", save_all=True, append_images=images[1:])
    return output.getvalue()


def test_student_source_asset_module_exposes_validation_boundary() -> None:
    """Missing source validation must fail before storage or model execution."""

    module = _validation_module()
    assert callable(getattr(module, "validate_student_source", None))


def test_valid_image_preserves_original_and_records_checksum() -> None:
    """Validation must not normalize or replace the Student's original bytes."""

    module = _validation_module()
    original = _png()
    source = module.validate_student_source(
        content=original,
        filename="work.PNG",
        content_type="image/png",
    )

    assert source.kind == "IMAGE"
    assert source.content == original
    assert source.size == len(original)
    assert source.checksum_sha256 == "af9cb484e25836824f7bf5adede1e0ce33aea0abaae1e8978b5ec30e99ca27f1"


def test_valid_docx_is_bounded_textual_document() -> None:
    module = _validation_module()
    source = module.validate_student_source(
        content=_docx(),
        filename="notes.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert source.kind == "DOCUMENT"
    assert source.filename == "notes.docx"


@pytest.mark.parametrize(
    ("content", "filename", "content_type", "message"),
    [
        (b"", "work.png", "image/png", "empty"),
        (_png(), "work.jpg", "image/jpeg", "does not match"),
        (_docx(), "notes.pdf", "application/pdf", "does not match"),
        (b"not-a-png", "work.png", "image/png", "invalid image"),
        (b"%PDF-1.4\n/Type /Page\n%%EOF", "work.pdf", "application/pdf", "invalid PDF"),
        (_png(), "..\\work.png", "image/png", "filename is invalid"),
    ],
)
def test_invalid_source_fails_before_storage(
    content: bytes, filename: str, content_type: str, message: str
) -> None:
    module = _validation_module()
    with pytest.raises(module.StudentSourceValidationError, match=message):
        module.validate_student_source(
            content=content,
            filename=filename,
            content_type=content_type,
        )


def test_source_size_and_image_pixel_bounds_are_application_owned() -> None:
    module = _validation_module()
    with pytest.raises(module.StudentSourceValidationError, match="size"):
        module.validate_student_source(
            content=_png(), filename="work.png", content_type="image/png", max_bytes=10
        )
    with pytest.raises(module.StudentSourceValidationError, match="pixels"):
        module.validate_student_source(
            content=_png(),
            filename="work.png",
            content_type="image/png",
            max_image_pixels=3,
        )
    with pytest.raises(module.StudentSourceValidationError, match="PDF pages"):
        module.validate_student_source(
            content=_pdf(pages=2),
            filename="work.pdf",
            content_type="application/pdf",
            max_pdf_pages=1,
        )


def test_student_source_asset_schema_keeps_bytes_out_of_postgres() -> None:
    """The durable asset row stores private lineage and metadata, never content."""

    models = importlib.import_module("services.platform.db.models")
    model = getattr(models, "StudentSourceAsset", None)
    assert model is not None
    assert set(model.__table__.columns.keys()) == {
        "id",
        "student_id",
        "learning_session_id",
        "source_message_id",
        "kind",
        "original_filename",
        "content_type",
        "size_bytes",
        "checksum_sha256",
        "storage_key",
        "created_at",
    }
    assert "content" not in model.__table__.columns
    assert "base64" not in model.__table__.columns
    assert "ocr" not in model.__table__.columns
    assert "source_asset_id" in models.LearningMessage.__table__.columns
    assert "source_asset_id" in models.AIExecution.__table__.columns
