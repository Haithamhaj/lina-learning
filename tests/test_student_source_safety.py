from __future__ import annotations

from io import BytesIO
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image

from services.model_gateway.openai_moderation_provider import (
    SourceModerationProviderError,
    SourceModerationSignal,
)
from services.platform.db.models import SafetyAudit
from services.platform.safety import SafetyAction, SafetyPolicyService


class _Session:
    def __init__(self) -> None:
        self.rows: list[object] = []

    def add(self, row: object) -> None:
        self.rows.append(row)

    def flush(self) -> None:
        return None


class _Provider:
    model = "omni-moderation-latest"

    def __init__(self, *signals: SourceModerationSignal, failure: Exception | None = None) -> None:
        self.signals = list(signals)
        self.failure = failure
        self.calls: list[dict[str, object]] = []

    def inspect(self, *, text: str, images: object) -> SourceModerationSignal:
        self.calls.append({"text": text, "images": tuple(images)})
        if self.failure is not None:
            raise self.failure
        return self.signals.pop(0) if self.signals else _signal()


def _signal(*categories: str) -> SourceModerationSignal:
    return SourceModerationSignal(
        model="omni-moderation-latest",
        flagged=bool(categories),
        true_categories=frozenset(categories),
        applied_input_types={category: ("text", "image") for category in categories},
    )


def _png(color: str = "white") -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 32), color).save(output, format="PNG")
    return output.getvalue()


def _pdf() -> bytes:
    output = BytesIO()
    Image.new("RGB", (64, 64), "white").save(output, format="PDF")
    return output.getvalue()


def _docx(*, text: str, image: bytes | None = None) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        )
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>",
        )
        if image is not None:
            archive.writestr("word/media/source.png", image)
    return output.getvalue()


def _service(provider: _Provider):
    from services.student_sources.safety import StudentSourceSafetyService

    session = _Session()
    return StudentSourceSafetyService(provider=provider, policy=SafetyPolicyService(session)), session


def test_image_safety_sends_actual_source_bytes_and_persists_only_bounded_audit() -> None:
    provider = _Provider(_signal())
    service, session = _service(provider)
    image = _png()
    student_id, message_id, asset_id = uuid4(), uuid4(), uuid4()

    decision = service.evaluate(
        student_id=student_id,
        source_message_id=message_id,
        source_asset_id=asset_id,
        student_text="Help me with this.",
        source_input={"kind": "IMAGE", "filename": "work.png", "content_type": "image/png", "content": image},
    )

    assert decision.action is SafetyAction.ALLOW
    assert len(provider.calls) == 1
    assert provider.calls[0]["text"] == "Help me with this."
    assert provider.calls[0]["images"][0].content == image
    audit = next(row for row in session.rows if isinstance(row, SafetyAudit))
    assert audit.interaction_ref == f"message:{message_id};source:{asset_id}"
    assert audit.policy_source == "SOURCE_MODERATION"
    assert audit.reason_code == "SOURCE_NORMAL_LEARNING"
    assert image not in repr(audit).encode()


def test_server_policy_maps_protected_categories_without_using_flagged_as_authority() -> None:
    provider = _Provider(_signal("self-harm/intent"), _signal("violence"))
    service, _ = _service(provider)
    common = {
        "student_id": uuid4(),
        "source_message_id": uuid4(),
        "source_asset_id": uuid4(),
        "student_text": "Help me with this.",
        "source_input": {"kind": "IMAGE", "filename": "work.png", "content_type": "image/png", "content": _png()},
    }

    blocked = service.evaluate(**common)
    limited = service.evaluate(**common)

    assert blocked.action is SafetyAction.BLOCK
    assert blocked.reason_code == "SOURCE_SELF_HARM_INTENT"
    assert limited.action is SafetyAction.AGE_APPROPRIATE_ONLY
    assert limited.reason_code == "SOURCE_SENSITIVE_AGE_APPROPRIATE"


def test_moderation_transport_failure_fails_closed_with_recoverable_message() -> None:
    provider = _Provider(failure=SourceModerationProviderError("network_error"))
    service, session = _service(provider)

    decision = service.evaluate(
        student_id=uuid4(),
        source_message_id=uuid4(),
        source_asset_id=uuid4(),
        student_text="Help",
        source_input={"kind": "IMAGE", "filename": "work.png", "content_type": "image/png", "content": _png()},
    )

    assert decision.action is SafetyAction.BLOCK
    assert decision.reason_code == "SOURCE_MODERATION_UNAVAILABLE"
    assert decision.directive == "I couldn't safely check that file right now. Please try again."
    assert next(row for row in session.rows if isinstance(row, SafetyAudit)).action == "BLOCK"


def test_pdf_pages_are_rendered_transiently_for_moderation() -> None:
    provider = _Provider(_signal())
    service, _ = _service(provider)

    decision = service.evaluate(
        student_id=uuid4(), source_message_id=uuid4(), source_asset_id=uuid4(),
        student_text="Explain the page.",
        source_input={"kind": "PDF", "filename": "page.pdf", "content_type": "application/pdf", "content": _pdf()},
    )

    assert decision.action is SafetyAction.ALLOW
    assert len(provider.calls) == 1
    assert provider.calls[0]["images"]
    assert all(image.content_type == "image/png" for image in provider.calls[0]["images"])


def test_docx_text_and_embedded_images_are_moderated_without_layout_rendering() -> None:
    provider = _Provider(_signal())
    service, _ = _service(provider)
    embedded = _png("blue")

    decision = service.evaluate(
        student_id=uuid4(), source_message_id=uuid4(), source_asset_id=uuid4(),
        student_text="Explain the notes.",
        source_input={
            "kind": "DOCUMENT",
            "filename": "notes.docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "content": _docx(text="Synthetic document safety text", image=embedded),
        },
    )

    assert decision.action is SafetyAction.ALLOW
    assert len(provider.calls) == 1
    assert provider.calls[0]["text"] == "Explain the notes.\nSynthetic document safety text"
    assert provider.calls[0]["images"][0].content == embedded


def test_malformed_docx_fails_closed_before_moderation_or_tutor() -> None:
    provider = _Provider(_signal())
    service, session = _service(provider)

    decision = service.evaluate(
        student_id=uuid4(), source_message_id=uuid4(), source_asset_id=uuid4(),
        student_text="Explain the notes.",
        source_input={
            "kind": "DOCUMENT", "filename": "notes.docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "content": b"malformed",
        },
    )

    assert decision.action is SafetyAction.BLOCK
    assert decision.reason_code == "SOURCE_MODERATION_UNAVAILABLE"
    assert provider.calls == []
    assert next(row for row in session.rows if isinstance(row, SafetyAudit)).action == "BLOCK"


def test_sensitive_educational_word_is_not_a_new_keyword_block_rule() -> None:
    provider = _Provider(_signal())
    service, _ = _service(provider)
    decision = service.evaluate(
        student_id=uuid4(), source_message_id=uuid4(), source_asset_id=uuid4(),
        student_text="Health lesson: give a safe definition for a child.",
        source_input={
            "kind": "DOCUMENT", "filename": "health.docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "content": _docx(text="A health lesson mentions suicide in a safe definition."),
        },
    )
    assert decision.action is SafetyAction.ALLOW
