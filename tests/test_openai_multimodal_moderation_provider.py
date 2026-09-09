from __future__ import annotations

import base64
import json
from urllib.error import HTTPError, URLError

import pytest


class _Response:
    def __init__(self, body: object) -> None:
        self._body = json.dumps(body).encode()

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _types():
    from services.model_gateway.openai_moderation_provider import (
        ModerationImage,
        OpenAIMultimodalModerationProvider,
        SourceModerationProviderError,
    )

    return ModerationImage, OpenAIMultimodalModerationProvider, SourceModerationProviderError


def test_provider_sends_actual_text_and_image_to_official_moderation_endpoint() -> None:
    ModerationImage, Provider, _ = _types()
    captured: dict[str, object] = {}
    raw = {
        "id": "modr-private",
        "model": "omni-moderation-latest",
        "results": [{
            "flagged": True,
            "categories": {"self-harm": True, "violence": False},
            "category_scores": {"self-harm": 0.99, "violence": 0.01},
            "category_applied_input_types": {
                "self-harm": ["text", "image"],
                "violence": ["image"],
            },
        }],
    }

    def send(request: object, *, timeout: float) -> _Response:
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response(raw)

    signal = Provider(
        api_key="not-a-real-secret",
        request_sender=send,
        timeout_seconds=12.0,
    ).inspect(
        text="current student text",
        images=(ModerationImage(content_type="image/png", content=b"actual-image-bytes"),),
    )

    request = captured["request"]
    body = json.loads(request.data)
    assert request.full_url == "https://api.openai.com/v1/moderations"
    assert request.get_header("Authorization") == "Bearer not-a-real-secret"
    assert captured["timeout"] == 12.0
    assert body == {
        "model": "omni-moderation-latest",
        "input": [
            {"type": "text", "text": "current student text"},
            {
                "type": "image_url",
                "image_url": {
                    "url": "data:image/png;base64,"
                    + base64.b64encode(b"actual-image-bytes").decode("ascii")
                },
            },
        ],
    }
    assert signal.flagged is True
    assert signal.true_categories == frozenset({"self-harm"})
    assert signal.applied_input_types == {
        "self-harm": ("text", "image"),
        "violence": ("image",),
    }
    assert not hasattr(signal, "raw_response")
    assert not hasattr(signal, "category_scores")


@pytest.mark.parametrize(
    "failure,code",
    [
        (URLError("private detail"), "network_error"),
        (TimeoutError("private timeout"), "timeout"),
        (HTTPError("https://api.openai.com", 500, "secret", {}, None), "provider_error"),
    ],
)
def test_provider_normalizes_transport_failures(failure: Exception, code: str) -> None:
    ModerationImage, Provider, ProviderError = _types()

    def fail(request: object, *, timeout: float) -> _Response:
        raise failure

    with pytest.raises(ProviderError) as caught:
        Provider(api_key="test", request_sender=fail).inspect(
            text="safe",
            images=(ModerationImage(content_type="image/jpeg", content=b"image"),),
        )
    assert caught.value.code == code
    assert "private" not in str(caught.value)
    assert "secret" not in str(caught.value)


def test_provider_rejects_invalid_or_empty_input_before_network() -> None:
    ModerationImage, Provider, _ = _types()
    provider = Provider(
        api_key="test",
        request_sender=lambda *_args, **_kwargs: pytest.fail("must not call provider"),
    )
    with pytest.raises(ValueError, match="input"):
        provider.inspect(text="", images=())
    with pytest.raises(ValueError, match="image type"):
        provider.inspect(
            text="safe",
            images=(ModerationImage(content_type="image/svg+xml", content=b"svg"),),
        )
