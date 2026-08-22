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


def test_student_math_surface_uses_tutor_language_and_a_child_safe_unavailable_state() -> None:
    """Catches child-facing Tutor mislabeling or processing detail leakage."""

    workspace = Path(__file__).parents[1]
    math_session = (workspace / "apps/web/components/student-math-session.tsx").read_text()

    assert "Tutor: " in math_session
    assert "Tutor is thinking…" in math_session
    assert "Lina: " not in math_session
    assert "Lina is thinking…" not in math_session
    assert "Math is getting ready." in math_session
    assert "finish setting up your book" in math_session
    assert 'if ("ready" in next) {\n            setLearningSession(null);\n            setError("");' in math_session
