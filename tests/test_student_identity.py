"""PostgreSQL contracts for shared authenticated identity to Student resolution."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from services.platform.db.connection import normalize_database_url
from services.platform.db.models import User
from services.platform.student_identity import resolve_student_for_authenticated_identity


pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="PostgreSQL DATABASE_URL is required for Student identity contracts",
)


def test_authenticated_student_identity_creates_then_reuses_one_student() -> None:
    """The verified external identity, never a browser Student id, owns resolution."""

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    subject = f"shared-identity-{uuid4().hex}"
    with Session(engine) as session:
        first = resolve_student_for_authenticated_identity(
            session,
            identity_provider="clerk",
            subject=subject,
            email="shared@example.test",
        )
        first_id = first.id
        session.commit()
    with Session(engine) as session:
        repeated = resolve_student_for_authenticated_identity(
            session,
            identity_provider="clerk",
            subject=subject,
            email="shared@example.test",
        )
        assert repeated.id == first_id
        session.commit()
    engine.dispose()


def test_non_student_identity_is_rejected_without_creating_a_student() -> None:
    """An existing non-Student User never receives a Student profile implicitly."""

    engine = create_engine(normalize_database_url(os.environ["DATABASE_URL"]))
    subject = f"non-student-{uuid4().hex}"
    with Session(engine) as session:
        session.add(User(identity_provider="clerk", external_subject=subject, role="PARENT_ADMIN"))
        session.commit()
    with Session(engine) as session:
        with pytest.raises(PermissionError):
            resolve_student_for_authenticated_identity(
                session,
                identity_provider="clerk",
                subject=subject,
                email=None,
            )
        session.rollback()
    engine.dispose()


def test_studio_route_has_no_tutor_module_import() -> None:
    """Studio's identity boundary is platform-owned, not hidden behind Tutor imports."""

    source = Path("apps/api/routes/studio.py").read_text()
    assert "services.tutor" not in source
