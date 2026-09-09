"""CS-04A durable admission tests."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from services.platform.db import models as m
from services.platform.db.connection import normalize_database_url
from services.studio.canvas_specialist import CanvasSpecialistAdmissionError, admit_committed_visual_order
from workers.studio_handlers import _settle

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="PostgreSQL DATABASE_URL is required")


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    with engine.begin() as c:
        c.execute(text("TRUNCATE jobs, studio_canvas_specialist_runs, studio_runtimes, learning_messages, learning_sessions, students, users CASCADE"))
    yield sessionmaker(engine, expire_on_commit=False)
    engine.dispose()


def _lineage(session: Session, *, status: str = "ADMITTED", capability: str = "process-capability-pack-v1") -> tuple[m.Student, m.LearningSession, m.LearningMessage]:
    user = m.User(identity_provider="cs04", external_subject=uuid4().hex); session.add(user); session.flush()
    student = m.Student(user_id=user.id, display_name="Test"); session.add(student); session.flush()
    learning = m.LearningSession(student_id=student.id, subject="SCIENCE", status="OPEN"); session.add(learning); session.flush()
    session.add(m.StudioRuntime(student_id=student.id, learning_session_id=learning.id)); session.flush()
    pack = {"version":"frozen-composition-pack-v1", "capability_pack":{"identity": capability}, "semantic_alignment":{}, "admitted_order":{}}
    digest = sha256(json.dumps(pack, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    message = m.LearningMessage(session_id=learning.id, role="tutor", content="Tutor", payload={"workspace_visual":{"status":status, "order_digest":digest, "frozen_composition_pack":pack}})
    session.add(message); session.flush(); return student, learning, message


def test_repeated_admission_is_one_job_and_one_run(factory: sessionmaker[Session]) -> None:
    with factory.begin() as s:
        student, learning, message = _lineage(s)
        first = admit_committed_visual_order(s, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id)
        second = admit_committed_visual_order(s, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id)
        assert first is not None and second is not None and first.id == second.id
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(m.Job)) == 1
        assert s.scalar(select(func.count()).select_from(m.StudioCanvasSpecialistRun)) == 1
        assert s.scalar(select(m.Job.max_attempts)) == 2


def test_non_executable_states_create_no_work(factory: sessionmaker[Session]) -> None:
    with factory.begin() as s:
        student, learning, message = _lineage(s, status="NOT_REQUESTED")
        assert admit_committed_visual_order(s, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id) is None
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(m.Job)) == 0
        assert s.scalar(select(func.count()).select_from(m.StudioCanvasSpecialistRun)) == 0


def test_historical_disabled_capability_cannot_admit(factory: sessionmaker[Session]) -> None:
    with factory.begin() as s:
        student, learning, message = _lineage(s, capability="SPECIALIST_CAPABILITY_PACK_V1")
        assert admit_committed_visual_order(s, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id) is None
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(m.Job)) == 0
        assert s.scalar(select(func.count()).select_from(m.StudioCanvasSpecialistRun)) == 0


def test_concurrent_admission_resolves_one_job_and_one_run(factory: sessionmaker[Session]) -> None:
    with factory.begin() as s:
        student, learning, message = _lineage(s)
        ids = (student.id, learning.id, message.id)

    def admit() -> str:
        with factory.begin() as s:
            run = admit_committed_visual_order(s, student_id=ids[0], learning_session_id=ids[1], source_message_id=ids[2])
            assert run is not None
            return str(run.id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        run_ids = list(pool.map(lambda _: admit(), range(2)))
    with factory() as s:
        assert len(set(run_ids)) == 1
        assert s.scalar(select(func.count()).select_from(m.Job)) == 1
        assert s.scalar(select(func.count()).select_from(m.StudioCanvasSpecialistRun)) == 1


def test_failure_after_job_resolution_rolls_back_job_and_run(factory: sessionmaker[Session]) -> None:
    with pytest.raises(RuntimeError):
        with factory.begin() as s:
            student, learning, message = _lineage(s)
            admit_committed_visual_order(s, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id, before_run_create=lambda: (_ for _ in ()).throw(RuntimeError("inject")))
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(m.Job)) == 0
        assert s.scalar(select(func.count()).select_from(m.StudioCanvasSpecialistRun)) == 0


@pytest.mark.parametrize("status,capability,mutate", [
    ("NOT_REQUESTED", "process-capability-pack-v1", None), ("REJECTED", "process-capability-pack-v1", None),
    ("ADMITTED", "SPECIALIST_CAPABILITY_PACK_V1", None), ("ADMITTED", "process-capability-pack-v1", "missing_pack"),
    ("ADMITTED", "process-capability-pack-v1", "bad_digest"),
])
def test_non_executable_or_invalid_pack_creates_no_work(factory: sessionmaker[Session], status: str, capability: str, mutate: str | None) -> None:
    with factory.begin() as s:
        student, learning, message = _lineage(s, status=status, capability=capability)
        visual = message.payload["workspace_visual"]
        if mutate == "missing_pack": visual["frozen_composition_pack"] = None
        if mutate == "bad_digest": visual["order_digest"] = "0" * 64
        if mutate is None or status == "ADMITTED":
            try: result = admit_committed_visual_order(s, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id)
            except CanvasSpecialistAdmissionError: result = None
            assert result is None
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(m.Job)) == 0 and s.scalar(select(func.count()).select_from(m.StudioCanvasSpecialistRun)) == 0


def test_wrong_student_or_session_creates_no_work(factory: sessionmaker[Session]) -> None:
    with factory.begin() as s:
        student, learning, message = _lineage(s)
        with pytest.raises(CanvasSpecialistAdmissionError): admit_committed_visual_order(s, student_id=uuid4(), learning_session_id=learning.id, source_message_id=message.id)
        with pytest.raises(CanvasSpecialistAdmissionError): admit_committed_visual_order(s, student_id=student.id, learning_session_id=uuid4(), source_message_id=message.id)
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(m.Job)) == 0 and s.scalar(select(func.count()).select_from(m.StudioCanvasSpecialistRun)) == 0


def test_foreign_session_tutor_message_is_rejected_without_side_effects(factory: sessionmaker[Session]) -> None:
    with factory.begin() as s:
        student, target, _ = _lineage(s)
        foreign = m.LearningSession(student_id=student.id, subject="SCIENCE", status="OPEN"); s.add(foreign); s.flush()
        s.add(m.StudioRuntime(student_id=student.id, learning_session_id=foreign.id)); s.flush()
        foreign_message = m.LearningMessage(session_id=foreign.id, role="tutor", content="other", payload={"workspace_visual": {"status": "ADMITTED"}}); s.add(foreign_message); s.flush()
        with pytest.raises(CanvasSpecialistAdmissionError, match="SOURCE_LINEAGE_INVALID"):
            admit_committed_visual_order(s, student_id=student.id, learning_session_id=target.id, source_message_id=foreign_message.id)
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(m.Job)) == 0
        assert s.scalar(select(func.count()).select_from(m.StudioCanvasSpecialistRun)) == 0
        assert s.scalar(select(func.count()).select_from(m.AIExecution)) == 0


def test_foreign_student_and_non_tutor_messages_are_rejected(factory: sessionmaker[Session]) -> None:
    with factory.begin() as s:
        student_a, learning_a, _ = _lineage(s)
        _, _, foreign_tutor = _lineage(s)
        student_message = m.LearningMessage(session_id=learning_a.id, role="student", content="hello", payload={"workspace_visual": {"status": "ADMITTED"}})
        s.add(student_message); s.flush()
        for source in (foreign_tutor, student_message):
            with pytest.raises(CanvasSpecialistAdmissionError, match="SOURCE_LINEAGE_INVALID"):
                admit_committed_visual_order(s, student_id=student_a.id, learning_session_id=learning_a.id, source_message_id=source.id)
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(m.Job)) == 0
        assert s.scalar(select(func.count()).select_from(m.StudioCanvasSpecialistRun)) == 0
        assert s.scalar(select(func.count()).select_from(m.AIExecution)) == 0


def test_missing_target_studio_runtime_is_rejected_without_work(factory: sessionmaker[Session]) -> None:
    with factory.begin() as s:
        student, learning, message = _lineage(s)
        runtime = s.scalar(select(m.StudioRuntime).where(m.StudioRuntime.learning_session_id == learning.id))
        s.delete(runtime); s.flush()
        with pytest.raises(CanvasSpecialistAdmissionError, match="STUDIO_RUNTIME_INVALID"):
            admit_committed_visual_order(s, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id)
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(m.Job)) == 0
        assert s.scalar(select(func.count()).select_from(m.StudioCanvasSpecialistRun)) == 0


def test_cancelled_run_never_accepts_a_late_specialist_proposal(factory: sessionmaker[Session]) -> None:
    """A provider response arriving after cancellation is durable but unusable."""
    with factory.begin() as s:
        student, learning, message = _lineage(s)
        run = admit_committed_visual_order(
            s,
            student_id=student.id,
            learning_session_id=learning.id,
            source_message_id=message.id,
        )
        assert run is not None
        run.status = "CANCELLED"
        run.failure_metadata = {"code": "CANCELLED_BY_APPLICATION"}
        run_id = run.id

    result = _settle(factory, run_id, {"proposal": "late"}, None)

    assert result["run_status"] == "CANCELLED"
    with factory() as s:
        run = s.get(m.StudioCanvasSpecialistRun, run_id)
        assert run is not None
        assert run.status == "CANCELLED"
        assert run.proposal_payload is None


def test_cancelled_run_keeps_late_provider_execution_lineage_without_proposal(factory: sessionmaker[Session]) -> None:
    with factory.begin() as s:
        student, learning, message = _lineage(s)
        run = admit_committed_visual_order(s, student_id=student.id, learning_session_id=learning.id, source_message_id=message.id)
        assert run is not None
        execution = m.AIExecution(task="canvas_specialist", provider="fixture", model="gpt-5.6-luna", latency_ms=1, success=True)
        s.add(execution); s.flush()
        run.status = "CANCELLED"
        run_id, execution_id = run.id, execution.id

    assert _settle(factory, run_id, {"proposal": "late"}, execution_id)["run_status"] == "CANCELLED"

    with factory() as s:
        run = s.get(m.StudioCanvasSpecialistRun, run_id)
        assert run is not None and run.status == "CANCELLED"
        assert run.ai_execution_id == execution_id and run.proposal_payload is None
