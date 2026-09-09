"""Deterministic transient text extraction from immutable Student DOCX files."""

from __future__ import annotations

from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


_WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_PARAGRAPH_TAG = f"{{{_WORD_NAMESPACE}}}p"
_TEXT_TAG = f"{{{_WORD_NAMESPACE}}}t"


class DocxExtractionError(ValueError):
    """The original DOCX cannot be read safely and deterministically."""


def extract_docx_text(content: bytes) -> str:
    """Return ordered paragraph text without persisting or interpreting it."""

    try:
        with ZipFile(BytesIO(content)) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
    except (BadZipFile, KeyError, ElementTree.ParseError, OSError) as error:
        raise DocxExtractionError("DOCX text extraction failed.") from error

    paragraphs: list[str] = []
    for paragraph in root.iter(_PARAGRAPH_TAG):
        text = "".join(node.text or "" for node in paragraph.iter(_TEXT_TAG)).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)
