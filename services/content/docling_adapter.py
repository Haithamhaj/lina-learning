"""Docling boundary that normalizes a supported document into source text."""

from io import BytesIO

from docling.datamodel.base_models import DocumentStream
from docling.document_converter import DocumentConverter


def extract_structural_markdown(source: str) -> str:
    """Use Docling's Markdown pipeline and retain its normalized structure."""

    result = DocumentConverter().convert(
        DocumentStream(name="fixture.md", stream=BytesIO(source.encode("utf-8")))
    )
    return result.document.export_to_markdown()
