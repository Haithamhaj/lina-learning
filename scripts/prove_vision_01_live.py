"""Bounded, opt-in VISION-01 proof through the authenticated application route."""

from __future__ import annotations

from io import BytesIO
import json
import os
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from services.platform.auth import AuthenticatedPrincipal, UserRole, get_current_principal
from services.platform.config import get_settings, reset_settings_cache
from services.platform.db.connection import normalize_database_url
from services.platform.db.models import AIExecution, LearningMessage, Student, StudentSourceAsset, User
from services.platform.db.session import get_session
from services.platform.storage import create_object_storage


def _educational_image() -> bytes:
    image = Image.new("RGB", (1200, 760), "white")
    draw = ImageDraw.Draw(image)
    draw.text((80, 80), "Grade 5 fraction work", fill="black", font_size=52)
    draw.text((80, 260), "3/4 + 1/4 = 4/8", fill="#17334f", font_size=86)
    draw.text((80, 430), "My submitted answer: 4/8", fill="#6658d3", font_size=58)
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def _educational_pdf() -> bytes:
    page = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(page)
    draw.text((90, 110), "Plant Measurement Note", fill="black", font_size=58)
    draw.text((90, 300), "Monday height: 12 cm", fill="#17334f", font_size=48)
    draw.text((90, 410), "Friday height: 18 cm", fill="#17334f", font_size=48)
    draw.text((90, 560), "Question: How much did the plant grow?", fill="#6658d3", font_size=42)
    output = BytesIO()
    page.save(output, "PDF", resolution=144.0)
    return output.getvalue()


def _terminal_text(response) -> str:
    assert response.status_code == 200, response.text
    turns = []
    for entry in response.text.split("\n\n"):
        if entry.startswith("event: turn\n"):
            turns.append(json.loads(entry.split("data: ", 1)[1]))
    assert len(turns) == 1, response.text
    return turns[0]["text"]


def main() -> None:
    if os.getenv("LINA_RUN_VISION_LIVE") != "1":
        raise SystemExit("Set LINA_RUN_VISION_LIVE=1 for the authorized bounded proof.")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url or not database_url.endswith("/lina_learning_test"):
        raise SystemExit("VISION-01 live proof requires the canonical disposable lina_learning_test database.")
    if os.getenv("MODEL_PROVIDER") != "openai" or os.getenv("MODEL_NAME") != "gpt-5.6-luna":
        raise SystemExit("VISION-01 live proof requires OpenAI gpt-5.6-luna explicitly.")

    reset_settings_cache()
    settings = get_settings()
    engine = create_engine(normalize_database_url(database_url))
    factory = sessionmaker(engine, expire_on_commit=False)
    proof_subject = f"vision-live-{uuid4()}"

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
    storage_keys: list[str] = []
    try:
        opened = client.post("/api/v1/student/daily/session")
        assert opened.status_code == 200, opened.text
        learning_session_id = opened.json()["learning_session_id"]
        image_response = client.post(
            f"/api/v1/student/daily/session/{learning_session_id}/source/turn/stream",
            files={"source": ("fraction-work.png", _educational_image(), "image/png")},
            data={"content": "What did I do wrong? State my submitted answer exactly."},
        )
        image_text = _terminal_text(image_response)
        image_asset_id = image_response.headers["X-Lina-Source-Asset-ID"]
        assert "4/8" in image_text, image_text

        followup_response = client.post(
            f"/api/v1/student/daily/session/{learning_session_id}/source/turn/stream",
            data={"content": "Why is that wrong?", "source_asset_id": image_asset_id},
        )
        followup_text = _terminal_text(followup_response)

        pdf_response = client.post(
            f"/api/v1/student/daily/session/{learning_session_id}/source/turn/stream",
            files={"source": ("plant-note.pdf", _educational_pdf(), "application/pdf")},
            data={"content": "According to the attached page, what was the plant height on Friday?"},
        )
        pdf_text = _terminal_text(pdf_response)
        assert "18" in pdf_text, pdf_text

        with factory() as session:
            user = session.execute(select(User).where(User.external_subject == proof_subject)).scalar_one()
            student = session.execute(select(Student).where(Student.user_id == user.id)).scalar_one()
            executions = session.execute(
                select(AIExecution).where(
                    AIExecution.student_id == student.id,
                    AIExecution.task == "tutor",
                ).order_by(AIExecution.created_at)
            ).scalars().all()
            assets = session.execute(
                select(StudentSourceAsset).where(StudentSourceAsset.student_id == student.id)
            ).scalars().all()
            messages = session.execute(
                select(LearningMessage).where(LearningMessage.session_id == UUID(learning_session_id)).order_by(LearningMessage.created_at)
            ).scalars().all()
            storage = create_object_storage(settings)
            originals = []
            for asset in assets:
                stored = storage.get(asset.storage_key)
                storage_keys.append(asset.storage_key)
                originals.append({
                    "asset_id": str(asset.id),
                    "kind": asset.kind,
                    "bytes_match": stored.metadata.checksum_sha256 == asset.checksum_sha256,
                    "source_message_id": str(asset.source_message_id),
                })
            result = {
                "provider": "openai",
                "model": "gpt-5.6-luna",
                "tutor_call_count": len(executions),
                "execution_source_asset_ids": [str(item.source_asset_id) for item in executions],
                "student_message_source_asset_ids": [str(item.source_asset_id) for item in messages if item.role == "student"],
                "image": {"source_meaning": "3/4 + 1/4 = 4/8; submitted answer 4/8", "response": image_text},
                "followup": {"source_asset_id": image_asset_id, "response": followup_text},
                "pdf": {"source_meaning": "Friday height is 18 cm", "response": pdf_text},
                "originals": originals,
            }
            assert len(executions) == 3, result
            assert len(assets) == 2, result
            assert executions[0].source_asset_id == executions[1].source_asset_id
            assert executions[2].source_asset_id != executions[0].source_asset_id
            assert all(original["bytes_match"] for original in originals)
            print(json.dumps(result, ensure_ascii=False, indent=2))
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
