"""Unit tests for the explicit OpenAI multipart transcription adapter."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from services.model_gateway.gateway import ModelRoute


VOICE_FIXTURES = Path(__file__).parent / "fixtures" / "voice"


class _Response:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _provider_types():
    from services.model_gateway.openai_transcription_provider import (
        OpenAITranscriptionProvider,
        TranscriptionProviderError,
        TranscriptionResponseError,
    )

    return OpenAITranscriptionProvider, TranscriptionProviderError, TranscriptionResponseError


def test_openai_transcription_provider_sends_multipart_and_normalizes_text() -> None:
    """A wrong endpoint, model, filename, type, or response key breaks this contract."""

    OpenAITranscriptionProvider, _, _ = _provider_types()
    captured: dict[str, object] = {}

    def send(request: object, *, timeout: float) -> _Response:
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response(json.dumps({"text": "  الكسر one half  "}).encode())

    result = OpenAITranscriptionProvider(
        api_key="not-a-real-secret",
        timeout_seconds=12.5,
        request_sender=send,
    ).execute(
        ModelRoute("openai", "gpt-transcribe"),
        {
            "audio": (VOICE_FIXTURES / "known-speech.wav").read_bytes(),
            "filename": "../../student phrase",
            "content_type": "audio/wav",
        },
    )

    request = captured["request"]
    body = request.data
    assert request.full_url == "https://api.openai.com/v1/audio/transcriptions"
    assert request.get_header("Authorization") == "Bearer not-a-real-secret"
    assert request.get_header("Content-type").startswith("multipart/form-data; boundary=")
    assert b'name="model"\r\n\r\ngpt-transcribe' in body
    assert b'name="response_format"\r\n\r\njson' in body
    assert b'name="file"; filename="student_phrase.wav"' in body
    assert b"Content-Type: audio/wav" in body
    assert (VOICE_FIXTURES / "known-speech.wav").read_bytes() in body
    assert captured["timeout"] == 12.5
    assert result.output == {"transcript": "الكسر one half"}
    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.estimated_cost_usd is None


def test_openai_transcription_provider_sends_completed_webm_with_matching_filename_and_type() -> None:
    OpenAITranscriptionProvider, _, _ = _provider_types()
    captured: dict[str, object] = {}
    audio = (VOICE_FIXTURES / "known-speech.webm").read_bytes()

    def send(request: object, *, timeout: float) -> _Response:
        captured["body"] = request.data
        return _Response(b'{"text":"A short spoken phrase.","languages":[{"code":"en"}]}')

    result = OpenAITranscriptionProvider(
        api_key="test-key", request_sender=send,
    ).execute(
        ModelRoute("openai", "gpt-transcribe"),
        {"audio": audio, "filename": "voice.webm", "content_type": "audio/webm"},
    )

    body = captured["body"]
    assert b'name="file"; filename="voice.webm"' in body
    assert b"Content-Type: audio/webm" in body
    assert audio in body
    assert result.output == {"transcript": "A short spoken phrase."}


@pytest.mark.parametrize("body", [b"{}", b"not-json"])
def test_openai_transcription_provider_rejects_missing_or_malformed_text(
    body: bytes,
) -> None:
    OpenAITranscriptionProvider, _, TranscriptionResponseError = _provider_types()

    provider = OpenAITranscriptionProvider(
        api_key="test-key",
        request_sender=lambda request, *, timeout: _Response(body),
    )

    with pytest.raises(TranscriptionResponseError, match="invalid transcription response"):
        provider.execute(
            ModelRoute("openai", "gpt-transcribe"),
            {"audio": b"audio", "filename": "audio.webm", "content_type": "audio/webm"},
        )


def test_openai_transcription_provider_distinguishes_a_blank_successful_transcript() -> None:
    from services.model_gateway.openai_transcription_provider import TranscriptionNoSpeechError

    OpenAITranscriptionProvider, _, _ = _provider_types()
    provider = OpenAITranscriptionProvider(
        api_key="test-key",
        request_sender=lambda request, *, timeout: _Response(b'{"text":"   ","languages":[]}'),
    )

    with pytest.raises(TranscriptionNoSpeechError):
        provider.execute(
            ModelRoute("openai", "gpt-transcribe"),
            {"audio": (VOICE_FIXTURES / "known-speech.wav").read_bytes(), "filename": "voice.wav", "content_type": "audio/wav"},
        )


@pytest.mark.parametrize(
    "failure,code",
    [
        (URLError("private network detail"), "network_error"),
        (TimeoutError("private timeout detail"), "timeout"),
        (HTTPError("https://api.openai.com", 500, "secret body", {}, None), "provider_error"),
    ],
)
def test_openai_transcription_provider_normalizes_transport_failures_without_details(
    failure: Exception,
    code: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    OpenAITranscriptionProvider, TranscriptionProviderError, _ = _provider_types()

    def fail(request: object, *, timeout: float) -> _Response:
        raise failure

    provider = OpenAITranscriptionProvider(api_key="test-key", request_sender=fail)

    with pytest.raises(TranscriptionProviderError) as caught:
        provider.execute(
            ModelRoute("openai", "gpt-transcribe"),
            {"audio": b"audio", "filename": "audio.webm", "content_type": "audio/webm"},
        )

    assert caught.value.code == code
    assert "private" not in str(caught.value)
    assert "secret" not in str(caught.value)
    assert "private" not in caplog.text
    assert "secret" not in caplog.text
    assert "test-key" not in caplog.text


def test_openai_transcription_provider_rejects_unapproved_content_type() -> None:
    OpenAITranscriptionProvider, _, _ = _provider_types()

    provider = OpenAITranscriptionProvider(
        api_key="test-key",
        request_sender=lambda request, *, timeout: pytest.fail(
            "Invalid media must be rejected before a network attempt."
        ),
    )

    with pytest.raises(ValueError, match="content type"):
        provider.execute(
            ModelRoute("openai", "gpt-transcribe"),
            {
                "audio": b"audio",
                "filename": "audio.wav",
                "content_type": "audio/wav\r\nX-Unsafe: true",
            },
        )
