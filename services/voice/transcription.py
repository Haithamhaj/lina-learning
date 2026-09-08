"""Validation and Model Gateway invocation for transient Student audio."""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from services.model_gateway.gateway import AIExecutionLineage, ModelGateway
from services.platform.db.models import ModelTask


_ALLOWED_AUDIO_EXTENSIONS = {
    "audio/webm": ".webm",
    "audio/wav": ".wav",
}


class EmptyAudioError(ValueError):
    pass


class UnsupportedAudioTypeError(ValueError):
    pass


class AudioTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class TranscriptionResult:
    transcript: str
    execution_id: UUID


def validated_audio_payload(
    *,
    audio: bytes,
    filename: str | None,
    content_type: str | None,
    max_audio_bytes: int,
) -> dict[str, object]:
    """Return the minimal transient payload accepted by the STT provider."""

    if not audio:
        raise EmptyAudioError("Audio is required.")
    if content_type not in _ALLOWED_AUDIO_EXTENSIONS:
        raise UnsupportedAudioTypeError("Audio type is not supported.")
    if len(audio) > max_audio_bytes:
        raise AudioTooLargeError("Audio exceeds the allowed size.")

    extension = _ALLOWED_AUDIO_EXTENSIONS[content_type]
    original = (filename or "audio").replace("\\", "/").rsplit("/", 1)[-1]
    stem = original.rsplit(".", 1)[0]
    safe_stem = re.sub(r"[^A-Za-z0-9_-]", "_", stem).strip("_") or "audio"
    return {
        "audio": audio,
        "filename": f"{safe_stem}{extension}",
        "content_type": content_type,
    }


def transcribe_student_audio(
    gateway: ModelGateway,
    *,
    student_id: UUID,
    learning_session_id: UUID,
    payload: dict[str, object],
) -> TranscriptionResult:
    """Run one synchronous STT operation with identifier-only lineage."""

    result = gateway.execute(
        ModelTask.SPEECH_TO_TEXT,
        payload,
        lineage=AIExecutionLineage(
            operation=ModelTask.SPEECH_TO_TEXT.value,
            student_id=student_id,
            learning_session_id=learning_session_id,
        ),
    )
    transcript = result.output.get("transcript")
    if not isinstance(transcript, str) or not transcript.strip() or result.execution_id is None:
        raise ValueError("Transcription result is invalid.")
    return TranscriptionResult(
        transcript=transcript.strip(),
        execution_id=result.execution_id,
    )
