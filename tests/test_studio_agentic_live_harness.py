from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from scripts import prove_studio_agentic_live as live
from scripts.prove_studio_agentic_live import LiveEvidenceRecorder
from services.platform.config.settings import Settings


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


def test_durable_live_action_selection_uses_a_tutor_triggering_scene_contract() -> None:
    """Catches a LIVE-09 harness accidentally choosing record-only FOCUS."""

    selector = getattr(live, "semantic_action_for_scene", None)
    assert callable(selector)
    action = selector({
        "version": "agentic-canvas-scene-v1",
        "objective": "Compare two exact values.",
        "subject_key": "MATH",
        "blocks": [{
            "block_id": "comparison-line",
            "type": "MATH_BOARD",
            "meaning": "Two exact markers on a number line.",
            "title": "Comparison",
            "accessibility": {"text_equivalent": "Two markers.", "aria_label": None},
            "allowed_actions": ["FOCUS", "SELECT"],
            "elements": [
                {"id": "smaller", "label": "3/5", "current_value": "3/5"},
                {"id": "larger", "label": "4/5", "current_value": "4/5"},
            ],
            "board_kind": "NUMBER_LINE",
            "axis_min": "0",
            "axis_max": "1",
        }],
    }, preferred_value="4/5")

    assert action == {
        "action_key": "SELECT",
        "payload": {
            "version": "agentic-canvas-action-v1",
            "action": "SELECT",
            "block_id": "comparison-line",
            "element_id": "larger",
            "from_value": None,
            "to_value": None,
        },
    }


def test_durable_evidence_connection_failure_becomes_a_bounded_case_failure(
    monkeypatch,
) -> None:
    def connection_failure(*_args, **_kwargs):
        raise ConnectionError("private database detail")

    monkeypatch.setattr(live, "_durable_studio_evidence", connection_failure)

    evidence, reason_code = live._try_durable_studio_evidence(
        Settings(_env_file=None, database_url="postgresql+psycopg://unused/unused"),
        uuid4(),
    )

    assert evidence is None
    assert reason_code == "ConnectionError"
