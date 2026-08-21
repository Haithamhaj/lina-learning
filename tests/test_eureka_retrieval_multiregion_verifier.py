"""Contract tests for the bounded real-Eureka multi-region retrieval golden."""

import importlib.util
from pathlib import Path
import sys


def _verifier():
    path = Path("scripts/verify_eureka_retrieval_multiregion.py")
    spec = importlib.util.spec_from_file_location(
        "eureka_retrieval_multiregion_verifier", path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_multiregion_golden_has_distinct_regions_and_focus_conflict() -> None:
    verifier = _verifier()
    cases = verifier.GOLDEN_CASES
    assert {case.expected_page for case in cases} == {2, 18, 30, 42}
    conflict = next(case for case in cases if case.name == "stale-focus-conflict")
    assert conflict.focus is not None
    assert conflict.expected_page == 18
    assert conflict.focus.concept_key == "p2:concept-place-value-shifts"
