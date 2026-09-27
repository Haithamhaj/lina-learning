"""Explicit multipart adapter for OpenAI file transcription requests."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from services.model_gateway.gateway import ModelResult, ModelRoute


_CONTENT_TYPE_EXTENSIONS = {
    "audio/webm": ".webm",
    "audio/wav": ".wav",
}
logger = logging.getLogger(__name__)


class TranscriptionProviderError(RuntimeError):
    """Safe normalized failure from the remote transcription service."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"OpenAI transcription failed ({code}).")


class TranscriptionResponseError(TranscriptionProviderError):
    """The provider returned no usable transcript."""

    def __init__(self, reason: str = "invalid_response") -> None:
        self.reason = reason
        super().__init__("invalid transcription response")


class TranscriptionNoSpeechError(TranscriptionProviderError):
    """A valid transcription response contained no audible speech text."""

    def __init__(self) -> None:
        super().__init__("no_speech")


class OpenAITranscriptionProvider:
    """Send transient audio to the OpenAI transcription endpoint."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
        request_sender: Callable[..., Any] = urlopen,
    ) -> None:
        self._api_key = api_key
        self._url = (
            f"{(base_url or 'https://api.openai.com').rstrip('/')}"
            "/v1/audio/transcriptions"
        )
        self._timeout_seconds = timeout_seconds
        self._request_sender = request_sender

    def execute(self, route: ModelRoute, payload: dict[str, object]) -> ModelResult:
        audio = payload.get("audio")
        filename = payload.get("filename")
        content_type = payload.get("content_type")
        if not isinstance(audio, bytes) or not isinstance(filename, str) or not isinstance(content_type, str):
            raise ValueError("Transcription payload is incomplete.")
        if content_type not in _CONTENT_TYPE_EXTENSIONS:
            raise ValueError("Transcription content type is not supported.")

        boundary = f"lina-{uuid4().hex}"
        body = _multipart_body(
            boundary=boundary,
            model=route.model,
            audio=audio,
            filename=_safe_filename(filename, content_type=content_type),
            content_type=content_type,
            context_hint=payload.get("context_hint"),
        )
        request = Request(
            self._url,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with self._request_sender(request, timeout=self._timeout_seconds) as response:
                raw_result = response.read()
                response_content_type = _safe_content_type(
                    getattr(response, "headers", None)
                )
        except HTTPError as error:
            logger.warning(
                "Transcription provider rejected request: http_status=%s audio_bytes=%s media_type=%s",
                error.code, len(audio), content_type,
            )
            raise TranscriptionProviderError("provider_error") from None
        except TimeoutError:
            logger.warning("Transcription provider timed out: audio_bytes=%s media_type=%s", len(audio), content_type)
            raise TranscriptionProviderError("timeout") from None
        except URLError as error:
            code = "timeout" if isinstance(error.reason, TimeoutError) else "network_error"
            logger.warning("Transcription provider transport failed: category=%s audio_bytes=%s media_type=%s", code, len(audio), content_type)
            raise TranscriptionProviderError(code) from None

        try:
            result = json.loads(raw_result)
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
            logger.warning("Transcription response rejected: category=malformed_json content_type=%s", response_content_type)
            raise TranscriptionResponseError("malformed_json") from None
        transcript = result.get("text") if isinstance(result, dict) else None
        if not isinstance(transcript, str):
            logger.warning(
                "Transcription response rejected: category=missing_text content_type=%s shape=%s",
                response_content_type,
                "object" if isinstance(result, dict) else type(result).__name__,
            )
            raise TranscriptionResponseError("missing_text")
        if not transcript.strip():
            logger.info("Transcription response contained no speech: content_type=%s", response_content_type)
            raise TranscriptionNoSpeechError()
        return ModelResult(output={"transcript": transcript.strip()})


def _safe_content_type(headers: object) -> str:
    value = headers.get("Content-Type", "") if hasattr(headers, "get") else ""
    media_type = value.split(";", 1)[0].strip().lower() if isinstance(value, str) else ""
    return media_type if re.fullmatch(r"[a-z0-9.+/-]{1,64}", media_type) else "unknown"


def _safe_filename(filename: str, *, content_type: str) -> str:
    leaf = filename.replace("\\", "/").rsplit("/", 1)[-1]
    normalized = re.sub(r"[^A-Za-z0-9._-]", "_", leaf).strip("._")
    extension = _CONTENT_TYPE_EXTENSIONS[content_type]
    if not normalized.lower().endswith(extension):
        normalized = f"{normalized or 'audio'}{extension}"
    return normalized or "audio.webm"


def _multipart_body(
    *,
    boundary: str,
    model: str,
    audio: bytes,
    filename: str,
    content_type: str,
    context_hint: object,
) -> bytes:
    delimiter = f"--{boundary}\r\n".encode()
    parts = [
        delimiter,
        b'Content-Disposition: form-data; name="model"\r\n\r\n',
        model.encode(),
        b"\r\n",
        delimiter,
        b'Content-Disposition: form-data; name="response_format"\r\n\r\n',
        b"json\r\n",
    ]
    if isinstance(context_hint, str) and context_hint.strip():
        parts.extend(
            [
                delimiter,
                b'Content-Disposition: form-data; name="prompt"\r\n\r\n',
                context_hint.strip().encode(),
                b"\r\n",
            ]
        )
    parts.extend(
        [
            delimiter,
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            audio,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(parts)
