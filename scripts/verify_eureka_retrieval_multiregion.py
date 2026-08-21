"""Verify bounded multi-region TASK-014 retrieval against real Eureka pages."""

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
    name: str
    question: str
    expected_semantic_key: str
    expected_source_ref: str
    expected_page: int
    focus: CurrentFocus | None = None
    maximum_unrelated_blocks: int = 1


GOLDEN_CASES = (
    GoldenCase(
        "place-value-exercise",
        "Help me multiply 3.452 by 100.",
        "p2:exercise-multiply-decimal-by-one-hundred",
        "EM_G5_M1_StudentWorkbook.pdf#page=2:item=32",
        2,
    ),
    GoldenCase(
        "metric-paraphrase",
        "How can I change meters into centimeters?",
        "p18:concept-metric-length-unit-conversion",
        "EM_G5_M1_StudentWorkbook.pdf#page=18:item=352",
        18,
    ),
    GoldenCase(
        "decimal-ordering",
        "Put these decimal numbers in increasing order.",
        "p30:exercise_arrange_decimals_in_increasing_order",
        "EM_G5_M1_StudentWorkbook.pdf#page=30:item=696",
        30,
    ),
    GoldenCase(
        "walking-trails",
        "Find the total distance for the walking trails.",
        "p42:exercise_total_trail_distance",
        "EM_G5_M1_StudentWorkbook.pdf#page=42:item=873",
        42,
    ),
    GoldenCase(
        "aligned-current-focus",
        "Can I practice converting meters to centimeters?",
        "p18:exercise-168-meters-to-centimeters",
        "EM_G5_M1_StudentWorkbook.pdf#page=18:item=363",
        18,
        CurrentFocus(concept_key="p18:concept-metric-length-unit-conversion"),
        0,
    ),
    GoldenCase(
        "stale-focus-conflict",
        "How many centimeters are in 3 meters?",
        "p18:example-three-meters-to-centimeters",
        "EM_G5_M1_StudentWorkbook.pdf#page=18:item=354",
        18,
        CurrentFocus(concept_key="p2:concept-place-value-shifts"),
        1,
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
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
                raise SystemExit("No Eureka source is present.")
            service = RetrievalService(
                session, embedding_gateway=create_embedding_gateway(session)
            )
            passed = 0
            for case in GOLDEN_CASES:
                context = service.retrieve_with_debug(
                    student_id=document.student_id,
                    question=case.question,
                    focus=case.focus,
                    candidate_limit=12,
                    block_limit=2,
                    character_budget=6000,
                )
                semantic_keys = {block.semantic_key for block in context.blocks}
                source_refs = {
                    source_ref
                    for block in context.blocks
                    for source_ref in block.source_refs
                }
                pages = {
                    page
                    for block in context.blocks
                    for page in block.page_numbers
                    if page is not None
                }
                unrelated = sum(
                    1
                    for block in context.blocks
                    if case.expected_page not in block.page_numbers
                )
                success = (
                    case.expected_semantic_key in semantic_keys
                    and case.expected_source_ref in source_refs
                    and case.expected_page in pages
                    and unrelated <= case.maximum_unrelated_blocks
                )
                print(
                    f"{case.name}: {'PASS' if success else 'FAIL'} "
                    f"blocks={len(context.blocks)} unrelated={unrelated}"
                )
                if args.show_output:
                    print(f"  keys={sorted(semantic_keys)} refs={sorted(source_refs)}")
                passed += int(success)
            print(
                f"Eureka multi-region retrieval golden: {passed}/{len(GOLDEN_CASES)} passed"
            )
            if passed != len(GOLDEN_CASES):
                raise SystemExit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
