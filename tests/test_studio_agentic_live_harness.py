from __future__ import annotations

import json
from pathlib import Path

from scripts.prove_studio_agentic_live import LiveEvidenceRecorder


def test_live_evidence_recorder_flushes_each_completed_scenario(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "proof.json"
    recorder = LiveEvidenceRecorder(output=output, model="gpt-live")

    recorder.record({"case_id": "LIVE-01", "status": "RUN", "passed": True})

    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence == {
        "proof": "STUDIO-AGENTIC-01",
        "schema_version": "studio-agentic-live-proof-v1",
        "model": "gpt-live",
        "run_status": "RUNNING",
        "all_required_passed": False,
        "results": [{"case_id": "LIVE-01", "status": "RUN", "passed": True}],
    }


def test_live_evidence_recorder_preserves_partial_results_on_failure(tmp_path: Path) -> None:
    output = tmp_path / "proof.json"
    recorder = LiveEvidenceRecorder(output=output, model="gpt-live")
    recorder.record({"case_id": "LIVE-01", "status": "RUN", "passed": True})

    recorder.fail(RuntimeError("provider response contained private text"))

    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["run_status"] == "FAILED"
    assert evidence["all_required_passed"] is False
    assert evidence["failure"] == {
        "exception_type": "RuntimeError",
        "last_completed_case_id": "LIVE-01",
    }
    assert "private text" not in output.read_text(encoding="utf-8")


def test_live_evidence_recorder_finalizes_complete_proof_atomically(tmp_path: Path) -> None:
    output = tmp_path / "proof.json"
    recorder = LiveEvidenceRecorder(output=output, model="gpt-live")
    results = [
        {"case_id": f"LIVE-{index:02d}", "status": "RUN", "passed": True}
        for index in range(1, 13)
    ]

    recorder.finish(results)

    evidence = json.loads(output.read_text(encoding="utf-8"))
    assert evidence["run_status"] == "COMPLETED"
    assert evidence["all_required_passed"] is True
    assert evidence["results"] == results
    assert not output.with_suffix(".json.tmp").exists()
