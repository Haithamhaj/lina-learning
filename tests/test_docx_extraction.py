from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest


def _docx(*paragraphs: tuple[str, ...]) -> bytes:
    body = "".join(
        "<w:p>" + "".join(f"<w:r><w:t>{run}</w:t></w:r>" for run in paragraph) + "</w:p>"
        for paragraph in paragraphs
    )
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0"?><w:document '
            'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body>{body}</w:body></w:document>",
        )
    return output.getvalue()


def test_extract_docx_text_reads_english_runs() -> None:
    from services.student_sources.docx import extract_docx_text

    assert extract_docx_text(_docx(("The plant grew ", "18 cm on Friday."))) == (
        "The plant grew 18 cm on Friday."
    )


def test_extract_docx_text_reads_arabic_without_reordering() -> None:
    from services.student_sources.docx import extract_docx_text

    assert extract_docx_text(_docx(("بلغ طول النبتة ", "١٨ سم يوم الجمعة."))) == (
        "بلغ طول النبتة ١٨ سم يوم الجمعة."
    )


def test_extract_docx_text_preserves_paragraph_and_run_order() -> None:
    from services.student_sources.docx import extract_docx_text

    assert extract_docx_text(
        _docx(("Observation: ", "Friday"), ("Height: ", "18 cm"), ("Next: ", "measure again"))
    ) == "Observation: Friday\nHeight: 18 cm\nNext: measure again"


@pytest.mark.parametrize("content", [b"not-a-zip", _docx(())[:-8]])
def test_extract_docx_text_rejects_malformed_documents(content: bytes) -> None:
    from services.student_sources.docx import DocxExtractionError, extract_docx_text

    with pytest.raises(DocxExtractionError):
        extract_docx_text(content)
