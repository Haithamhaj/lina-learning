"""One-call live proof for deterministic DOCX comprehension."""

from __future__ import annotations

from io import BytesIO
import json
import os
from uuid import UUID, uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
from services.platform.config import get_settings, reset_settings_cache
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import AIExecution, LearningMessage, Student, StudentSourceAsset, User
from services.platform.db.session import get_session
from services.platform.storage import create_object_storage


QUESTION = "How tall was the plant on Friday?"
SOURCE_TEXT = "The plant grew 18 cm on Friday."


def _docx() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types '
            'xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0"?><w:document '
            'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{SOURCE_TEXT}</w:t></w:r></w:p></w:body>"
            "</w:document>",
        )
    return output.getvalue()


def _terminal_text(response) -> str:
    assert response.status_code == 200, response.text
    turns = [
        json.loads(entry.split("data: ", 1)[1])
        for entry in response.text.split("\n\n")
        if entry.startswith("event: turn\n")
    ]
    assert len(turns) == 1, response.text
    return turns[0]["text"]


def main() -> None:
    if os.getenv("LINA_RUN_DOCX_COMPREHENSION_LIVE") != "1":
        raise SystemExit("Set LINA_RUN_DOCX_COMPREHENSION_LIVE=1 for this authorized proof.")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url or not database_url.endswith("/lina_learning_test"):
        raise SystemExit("The DOCX proof requires the disposable lina_learning_test database.")
    if os.getenv("MODEL_PROVIDER") != "openai" or os.getenv("MODEL_NAME") != "gpt-5.6-luna":
        raise SystemExit("The DOCX proof requires OpenAI gpt-5.6-luna explicitly.")

    reset_settings_cache()
    settings = get_settings()
    engine = create_engine(normalize_database_url(database_url))
    factory = sessionmaker(engine, expire_on_commit=False)
    proof_subject = f"docx-comprehension-live-{uuid4()}"
    storage_keys: list[str] = []

    def database_session():
        with factory.begin() as session:
            yield session

    from apps.api.main import app

    app.dependency_overrides[get_session] = database_session
    app.dependency_overrides[get_current_principal] = lambda: AuthenticatedPrincipal(
        subject=proof_subject,
        role=UserRole.STUDENT,
        email=f"{proof_subject}@example.test",
    )
    client = TestClient(app, raise_server_exceptions=True)
    try:
        opened = client.post("/api/v1/student/daily/session")
        learning_session_id = opened.json()["learning_session_id"]
        response = client.post(
            f"/api/v1/student/daily/session/{learning_session_id}/source/turn/stream",
            files={
                "source": (
                    "plant-observation.docx",
                    _docx(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            data={"content": QUESTION},
        )
        answer = _terminal_text(response)
        assert "18 cm" in answer, answer

        with factory() as session:
            user = session.execute(select(User).where(User.external_subject == proof_subject)).scalar_one()
            student = session.execute(select(Student).where(Student.user_id == user.id)).scalar_one()
            messages = session.execute(select(LearningMessage).where(
                LearningMessage.session_id == UUID(learning_session_id)
            ).order_by(LearningMessage.created_at)).scalars().all()
            executions = session.execute(select(AIExecution).where(
                AIExecution.student_id == student.id,
                AIExecution.task == "tutor",
            )).scalars().all()
            assets = session.execute(select(StudentSourceAsset).where(
                StudentSourceAsset.student_id == student.id,
            )).scalars().all()
            assert len(executions) == 1
            assert len(assets) == 1
            assert [message.content for message in messages if message.role == "student"] == [QUESTION]
            assert "extracted_text" not in json.dumps(
                [message.payload for message in messages], default=str
            )
            assert "prompt" not in AIExecution.__table__.columns
            assert "payload" not in AIExecution.__table__.columns
            assert "extracted_text" not in StudentSourceAsset.__table__.columns
            storage_keys.extend(asset.storage_key for asset in assets)
            print(json.dumps({
                "model": "gpt-5.6-luna",
                "question": QUESTION,
                "answer": answer,
                "tutor_call_count": len(executions),
                "student_message_content": QUESTION,
                "derived_text_persisted": False,
                "original_docx_remains_authority": True,
                "source_asset_id": str(assets[0].id),
                "execution_source_asset_id": str(executions[0].source_asset_id),
            }, ensure_ascii=False, indent=2))
    finally:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_current_principal, None)
        storage = create_object_storage(settings)
        for key in storage_keys:
            storage.delete(key)
        with factory.begin() as session:
            user = session.execute(select(User).where(User.external_subject == proof_subject)).scalar_one_or_none()
            if user is not None:
                session.delete(user)
        engine.dispose()


if __name__ == "__main__":
    main()
