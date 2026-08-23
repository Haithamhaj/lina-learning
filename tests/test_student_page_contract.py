"""A small web/API contract guard for the real Student surface."""

from pathlib import Path


def test_student_page_calls_the_authenticated_backend_path_not_demo_state() -> None:
    workspace = Path(__file__).parents[1]
    page = (workspace / "apps/web/app/student/page.tsx").read_text()
    math_session = (workspace / "apps/web/components/student-math-session.tsx").read_text()

    assert "StudentMathSession" in page
    assert "/v1/student/math/session" in math_session
    assert "/turn/stream" in math_session
    assert "/v1/demo" not in page + math_session


def test_student_math_surface_uses_tutor_language_without_a_content_readiness_block() -> None:
    """Catches child-facing Tutor mislabeling or a zero-content readiness block."""

    workspace = Path(__file__).parents[1]
    math_session = (workspace / "apps/web/components/student-math-session.tsx").read_text()

    assert 'message.role === "tutor" ? "Tutor" : "Lina"' in math_session
    assert "Tutor is thinking…" in math_session
    assert "Lina: " not in math_session
    assert "Lina is thinking…" not in math_session
    assert "MathUnavailable" not in math_session
    assert "setLearningSession(next);" in math_session


def test_student_math_surface_has_lina_tutor_visual_and_bilingual_ready_markers() -> None:
    """Catches loss of the visual distinction and direction-aware child chat treatment."""

    workspace = Path(__file__).parents[1]
    math_session = (workspace / "apps/web/components/student-math-session.tsx").read_text()

    assert 'message.role === "tutor" ? "Tutor" : "Lina"' in math_session
    assert 'dir="auto"' in math_session
    assert "Welcome to Math" in math_session
    assert "Tutor is thinking…" in math_session
