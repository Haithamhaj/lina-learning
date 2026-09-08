"""Unit contracts for the application-owned speech-to-text route."""

from __future__ import annotations

from types import SimpleNamespace

from services.platform.config import Settings
from services.platform.db.models import ModelTask


def test_speech_to_text_has_an_independent_configured_model_route() -> None:
    """Changing the Tutor model must not change the transcription route."""

    from services.model_gateway.factory import create_speech_to_text_gateway

    provider = SimpleNamespace(execute=lambda route, payload: None)
    settings = Settings(
        _env_file=None,
        model_provider="mock",
        model_name="primary-tutor-model",
        transcription_model_name="independent-transcription-model",
    )

    gateway = create_speech_to_text_gateway(
        SimpleNamespace(),
        settings=settings,
        local_provider=provider,
    )

    assert ModelTask.SPEECH_TO_TEXT.value == "speech_to_text"
    assert gateway.route_for(ModelTask.SPEECH_TO_TEXT).provider == "local-demo"
    assert gateway.route_for(ModelTask.SPEECH_TO_TEXT).model == "independent-transcription-model"


def test_speech_to_text_openai_route_uses_the_explicit_transcription_provider() -> None:
    from services.model_gateway.factory import create_speech_to_text_gateway

    provider = SimpleNamespace(execute=lambda route, payload: None)
    gateway = create_speech_to_text_gateway(
        SimpleNamespace(),
        settings=Settings(
            _env_file=None,
            model_provider="openai",
            model_api_key="test-key",
            model_name="primary-tutor-model",
            transcription_model_name="gpt-transcribe",
        ),
        openai_provider=provider,
    )

    assert gateway.route_for(ModelTask.SPEECH_TO_TEXT).provider == "openai"
    assert gateway.route_for(ModelTask.SPEECH_TO_TEXT).model == "gpt-transcribe"


def test_speech_to_text_configuration_has_a_bounded_default_upload_size() -> None:
    settings = Settings(_env_file=None)

    assert settings.transcription_model_name == "gpt-transcribe"
    assert settings.transcription_max_audio_bytes == 5 * 1024 * 1024
