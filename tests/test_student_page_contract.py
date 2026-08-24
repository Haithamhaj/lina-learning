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


def test_student_math_surface_keeps_only_latest_tutor_actions_active_and_input_editable_while_streaming() -> None:
    """Catches action chips becoming historical controls or disabling Lina's next thought while a turn streams."""

    workspace = Path(__file__).parents[1]
    math_session = (workspace / "apps/web/components/student-math-session.tsx").read_text()

    assert "suggested_actions" in math_session
    assert "latestTutorMessage" in math_session
    assert "sendMessage" in math_session
    assert "suggested_action: suggestedAction" in math_session
    assert "suggestedAction: true" in math_session
    assert "suggestedActionKind: action.kind" in math_session
    assert "if (!suggestedAction) setDraft(\"\");" in math_session
    input_start = math_session.index('id="student-math-message"')
    input_end = math_session.index("/>", input_start)
    assert "disabled=" not in math_session[input_start:input_end]


def test_student_math_surface_records_a_private_stream_lifecycle_without_changing_ready_after_eof() -> None:
    """OBS-01: a delayed EOF must remain distinguishable from the terminal Tutor event."""

    workspace = Path(__file__).parents[1]
    math_session = (workspace / "apps/web/components/student-math-session.tsx").read_text()

    assert "createTutorStreamLifecycleTrace" in math_session
    assert "terminal_turn_received" in math_session
    assert "stream_eof" in math_session
    assert "ui_ready" in math_session
    send_message = math_session.index("const sendMessage")
    assert math_session.index('record("terminal_turn_received")', send_message) < math_session.index('record("stream_eof")', send_message)
    assert math_session.index('record("stream_eof")', send_message) < math_session.index('setState("ready")', send_message)
    assert math_session.index('setState("ready")', send_message) < math_session.index('record("ui_ready")', send_message)
