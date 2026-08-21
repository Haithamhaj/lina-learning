"""Verify TASK-014 retrieval quality against local, indexed Eureka content.

The workbook remains in the ignored ``.local/eureka`` cache. This verifier uses
the bounded real pages 1–2 golden region prepared by the companion script.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from services.model_gateway.factory import create_embedding_gateway
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import ContentDocument
from services.retrieval.service import CurrentFocus, RetrievalService


@dataclass(frozen=True)
class GoldenCase:
    style: str
    question: str
    expected_semantic_type: str
    expected_source_ref: str
    expected_page: int
    focus: CurrentFocus | None = None


GOLDEN_CASES = (
    GoldenCase(
        "terminology",
        "What is place value?",
        "CONCEPT",
        "EM_G5_M1_StudentWorkbook.pdf#page=2:item=20",
        2,
    ),
    GoldenCase(
        "paraphrase",
        "What happens to a decimal digit when it moves one place?",
        "CONCEPT",
        "EM_G5_M1_StudentWorkbook.pdf#page=2:item=20",
        2,
    ),
    GoldenCase(
        "example",
        "Show me an example for this place value lesson.",
        "EXAMPLE",
        "EM_G5_M1_StudentWorkbook.pdf#page=2:item=22",
        2,
    ),
    GoldenCase(
        "exercise",
        "Help me try the place value practice problem.",
        "EXERCISE",
        "EM_G5_M1_StudentWorkbook.pdf#page=2:item=32",
        2,
    ),
    GoldenCase(
        "figure",
        "What does the picture in this place value page show?",
        "FIGURE",
        "EM_G5_M1_StudentWorkbook.pdf#page=2:item=15",
        2,
    ),
    GoldenCase(
        "with-focus",
        "Can I practice this now?",
        "EXERCISE",
        "EM_G5_M1_StudentWorkbook.pdf#page=2:item=32",
        2,
        CurrentFocus(lesson_key="lesson-place-value-decimal-multiplication"),
    ),
    GoldenCase(
        "without-focus",
        "What should I practice in place value?",
        "EXERCISE",
        "EM_G5_M1_StudentWorkbook.pdf#page=2:item=32",
        2,
    ),
)


def case_passes(
    case: GoldenCase, *, semantic_types: set[str | None], source_refs: set[str]
) -> bool:
    return (
        case.expected_semantic_type in semantic_types
        and case.expected_source_ref in source_refs
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        required=True,
        help="Disposable PostgreSQL database with an indexed Eureka golden region.",
    )
    parser.add_argument("--filename", default="EM_G5_M1_StudentWorkbook.pdf")
    parser.add_argument("--show-output", action="store_true")
    args = parser.parse_args()
    engine = create_engine(normalize_database_url(args.database_url))
    try:
        with Session(engine) as session:
            document = (
                session.execute(
                    select(ContentDocument)
                    .where(ContentDocument.filename == args.filename)
                    .order_by(ContentDocument.created_at.desc())
                )
                .scalars()
                .first()
            )
            if document is None:
                raise SystemExit(
                    "No indexed Eureka source is present. Run scripts/prepare_eureka_retrieval_golden.py first."
                )
            gateway = create_embedding_gateway(session)
            service = RetrievalService(session, embedding_gateway=gateway)
            passed = 0
            for case in GOLDEN_CASES:
                context = service.retrieve_with_debug(
                    student_id=document.student_id,
                    question=case.question,
                    focus=case.focus,
                    candidate_limit=12,
                    block_limit=6,
                    character_budget=6000,
                )
                semantic_types = {block.semantic_type for block in context.blocks}
                source_refs = {
                    source_ref
                    for block in context.blocks
                    for source_ref in block.source_refs
                }
                success = case_passes(
                    case, semantic_types=semantic_types, source_refs=source_refs
                )
                print(
                    f"{case.style}: {'PASS' if success else 'FAIL'} blocks={len(context.blocks)} lexical={len(context.debug.lexical_block_ids)} vector={len(context.debug.vector_block_ids)}"
                )
                if args.show_output:
                    print(
                        f"  types={sorted(semantic_types)} refs={sorted(source_refs)}"
                    )
                passed += int(success)
            print(f"Eureka retrieval golden: {passed}/{len(GOLDEN_CASES)} passed")
            if passed != len(GOLDEN_CASES):
                raise SystemExit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
