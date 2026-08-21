"""Contract tests for the TASK-014 real-Eureka retrieval golden set."""

import importlib.util
from pathlib import Path
import sys


def _verifier():
    path = Path("scripts/verify_eureka_retrieval.py")
    spec = importlib.util.spec_from_file_location("eureka_retrieval_verifier", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_eureka_retrieval_golden_covers_required_question_styles() -> None:
    verifier = _verifier()
    styles = {case.style for case in verifier.GOLDEN_CASES}
    assert {
        "terminology",
        "paraphrase",
        "example",
        "exercise",
        "figure",
        "with-focus",
        "without-focus",
    } <= styles


def test_eureka_retrieval_golden_requires_matched_content_and_expected_provenance() -> (
    None
):
    verifier = _verifier()
    case = verifier.GOLDEN_CASES[0]
    assert verifier.case_passes(
        case,
        semantic_types={case.expected_semantic_type},
        source_refs={case.expected_source_ref},
    )
    assert not verifier.case_passes(
        case, semantic_types={case.expected_semantic_type}, source_refs={"wrong"}
    )
