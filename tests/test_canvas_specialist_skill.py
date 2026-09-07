"""CS-01 runtime Skill and Primary Tutor instruction-isolation contracts."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECIALIST_SKILL = ROOT / "runtime/canvas-specialist/SKILL.md"
CAPABILITY_PACK = ROOT / "runtime/canvas-specialist/visual-capability-pack-v1.md"
EXECUTION_PACK = ROOT / "runtime/canvas-specialist/process-capability-pack-v1.md"
DEVELOPMENT_SKILL = ROOT / "skills/lina-educational-visuals/SKILL.md"


def test_primary_tutor_loads_only_its_accepted_visual_guidance():
    from services.tutor.runtime import build_tutor_model_payload

    payload = build_tutor_model_payload(question="Explain a process.")
    instructions = payload["instructions"]

    assert "VISUAL_GUIDANCE_V1" in instructions
    assert "CANVAS_SPECIALIST_VISUAL_LEARNING_COMPOSER_V1" not in instructions
    assert "SPECIALIST_CAPABILITY_PACK_V1" not in instructions
    assert DEVELOPMENT_SKILL.read_text() not in instructions


def test_specialist_skill_preserves_authority_and_composition_boundaries():
    skill = " ".join(SPECIALIST_SKILL.read_text().split())

    required_markers = (
        "CANVAS_SPECIALIST_VISUAL_LEARNING_COMPOSER_V1",
        "Primary Tutor is the sole Student-facing teaching authority.",
        "competing lesson or teaching dialogue",
        "cannot choose renderer or implementation technology",
        "cannot output executable SVG, HTML, JavaScript, or CSS",
        "cannot persist anything directly",
        "bypass Safety or Parent Boundary",
        "cannot write Evidence, Candidate Events, Personal Facts, Learner Intelligence, State, or Patterns",
        "must not expand beyond the exact active Capability Pack",
        "Pre-output self-review",
    )

    for marker in required_markers:
        assert marker in skill


def test_capability_pack_is_per_run_bounded_and_not_execution_authorization():
    pack = " ".join(CAPABILITY_PACK.read_text().split())

    required_markers = (
        "SPECIALIST_CAPABILITY_PACK_V1",
        "per-run",
        "not the general Specialist intelligence definition",
        "not execution authorization by itself",
        "Natural production Process composition is not enabled",
        "2–8 stages",
        "application-owned renderer/layout/motion/IDs/persistence",
    )

    for marker in required_markers:
        assert marker in pack


def test_worker_uses_the_committed_execution_pack_not_the_disabled_historical_pack():
    from workers.studio_handlers import _instructions

    instructions = _instructions()
    assert EXECUTION_PACK.read_text() in instructions
    assert CAPABILITY_PACK.read_text() not in instructions
