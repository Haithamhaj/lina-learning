"""Verify TASK-011 structural retention against the ignored local Eureka PDF.

The workbook is development/test content only and remains outside Git under
``.local/eureka``.  With ``--database-url`` this script performs the same
Content-domain processing into the caller's disposable database, then compares
the persisted tree with the adapter result.  It never targets the sandbox demo
database by default.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from services.content.docling_adapter import extract_structural_items
from services.content.ingestion import ingest_source_document
from services.content.processing import process_structural_document
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import DocumentStructuralItem, Student, User
from services.platform.storage import LocalObjectStorage


DEFAULT_PDF = Path(".local/eureka/EM_G5_M1_StudentWorkbook.pdf")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument(
        "--database-url",
        help="Optional disposable PostgreSQL database URL for persisted-tree verification.",
    )
    args = parser.parse_args()
    if not args.pdf.is_file():
        raise SystemExit(f"Eureka PDF is not available at {args.pdf}. Run scripts/setup_eureka_demo.py first.")

    content = args.pdf.read_bytes()
    normalized = extract_structural_items(
        content_type="application/pdf", content=content, filename=args.pdf.name
    )
    _assert_adapter_structure(normalized)
    print(_summary("adapter", normalized))
    if args.database_url:
        _verify_persisted_structure(args.database_url, content, args.pdf.name, normalized)


def _assert_adapter_structure(items: list[object]) -> None:
    if not items:
        raise SystemExit("Docling produced no structural items.")
    keys = [item.item_key for item in items]
    if len(keys) != len(set(keys)):
        raise SystemExit("Normalized structural item keys are not unique within the run.")
    if max(item.hierarchy_depth for item in items) < 1:
        raise SystemExit("Docling output did not retain a structural hierarchy.")
    if not any(item.parent_item_key is not None for item in items):
        raise SystemExit("Docling output did not retain parent/child links.")
    if not any(item.page_number is not None for item in items):
        raise SystemExit("Docling output did not retain page provenance.")


def _verify_persisted_structure(
    database_url: str,
    content: bytes,
    filename: str,
    normalized: list[object],
) -> None:
    engine = create_engine(normalize_database_url(database_url))
    try:
        with TemporaryDirectory(prefix="lina-task011-") as storage_directory:
            storage = LocalObjectStorage(Path(storage_directory), signing_secret="task011-verification")
            with Session(engine) as session:
                user = User(identity_provider="task011-verification", external_subject=uuid4().hex)
                session.add(user)
                session.flush()
                student = Student(user_id=user.id, display_name="TASK-011 verification fixture")
                session.add(student)
                session.flush()
                document = ingest_source_document(
                    session,
                    storage=storage,
                    student_id=student.id,
                    grade_level=5,
                    subject="MATH",
                    filename=filename,
                    content_type="application/pdf",
                    content=content,
                )
                run = process_structural_document(session, storage=storage, document=document)
                if run.status != "COMPLETED":
                    raise SystemExit(f"Structural processing failed: {run.failure_detail}")
                persisted = (
                    session.query(DocumentStructuralItem)
                    .filter_by(processing_run_id=run.id)
                    .order_by(DocumentStructuralItem.reading_order)
                    .all()
                )
                if len(persisted) != len(normalized):
                    raise SystemExit(
                        f"Persisted item count {len(persisted)} differs from adapter count {len(normalized)}."
                    )
                if [item.item_key for item in persisted] != [item.item_key for item in normalized]:
                    raise SystemExit("Persisted stable item keys differ from adapter output.")
                if not any(item.parent_id is not None for item in persisted):
                    raise SystemExit("Persisted structural tree has no parent links.")
                if not any(item.page_number is not None for item in persisted):
                    raise SystemExit("Persisted structural tree has no page provenance.")
                session.commit()
                print(_summary("persisted", persisted))
                print(f"persisted run={run.id} document={document.id} status={run.status}")
    finally:
        engine.dispose()


def _summary(label: str, items: list[object]) -> str:
    types = Counter(item.item_type for item in items)
    max_depth = max(item.hierarchy_depth for item in items)
    pages = len({item.page_number for item in items if item.page_number is not None})
    return (
        f"{label}: items={len(items)} max_depth={max_depth} pages_with_provenance={pages} "
        f"types={dict(sorted(types.items()))}"
    )


if __name__ == "__main__":
    main()
