"""A small web/API contract guard for the real Student surface."""

from pathlib import Path


def test_student_page_calls_the_authenticated_backend_path_not_demo_state() -> None:
    workspace = Path(__file__).parents[1]
    page = (workspace / "apps/web/app/student/page.tsx").read_text()
    math_session = (workspace / "apps/web/components/student-math-session.tsx").read_text()

    assert "StudentMathSession" in page
    assert "/v1/student/math/session" in math_session
    assert "/v1/demo" not in page + math_session
