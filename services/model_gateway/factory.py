"""Configured Model Gateway construction for application tasks."""

from __future__ import annotations

from sqlalchemy.orm import Session

from services.model_gateway.gateway import ModelGateway, ModelProvider, ModelRoute
from services.model_gateway.openai_provider import OpenAIResponsesProvider
from services.model_gateway.openai_embedding_provider import OpenAIEmbeddingProvider
from services.platform.config import Settings, get_settings
from services.platform.db.models import ModelTask


def create_tutor_gateway(
    session: Session,
    *,
    local_provider: ModelProvider | None = None,
    settings: Settings | None = None,
    openai_provider: ModelProvider | None = None,
) -> ModelGateway:
    """Route the Tutor task through the configured provider boundary."""

    configured = settings or get_settings()
    if configured.model_provider == "openai":
        provider = openai_provider
        if provider is None:
            if configured.model_api_key is None:
                raise ValueError("MODEL_API_KEY is required for the OpenAI Tutor route.")
            provider = OpenAIResponsesProvider(
                api_key=configured.model_api_key.get_secret_value(),
                base_url=configured.model_base_url,
            )
        return ModelGateway(
            session,
            routes={ModelTask.TUTOR: ModelRoute("openai", configured.model_name)},
            providers={"openai": provider},
        )

    if local_provider is None:
        raise ValueError("A local provider is required when MODEL_PROVIDER=mock.")
    return ModelGateway(
        session,
        routes={ModelTask.TUTOR: ModelRoute("local-demo", configured.model_name)},
        providers={"local-demo": local_provider},
    )


def create_curriculum_semantics_gateway(
    session: Session,
    *,
    local_provider: ModelProvider | None = None,
    settings: Settings | None = None,
    openai_provider: ModelProvider | None = None,
) -> ModelGateway:
    """Route curriculum semantics through the configured provider boundary."""

    configured = settings or get_settings()
    if configured.model_provider == "openai":
        provider = openai_provider
        if provider is None:
            if configured.model_api_key is None:
                raise ValueError("MODEL_API_KEY is required for the OpenAI curriculum semantics route.")
            provider = OpenAIResponsesProvider(
                api_key=configured.model_api_key.get_secret_value(),
                base_url=configured.model_base_url,
            )
        return ModelGateway(
            session,
            routes={ModelTask.CURRICULUM_SEMANTICS: ModelRoute("openai", configured.model_name)},
            providers={"openai": provider},
        )

    if local_provider is None:
        raise ValueError("A local provider is required when MODEL_PROVIDER=mock.")
    return ModelGateway(
        session,
        routes={ModelTask.CURRICULUM_SEMANTICS: ModelRoute("local-demo", configured.model_name)},
        providers={"local-demo": local_provider},
    )


def create_embedding_gateway(session: Session, *, local_provider: ModelProvider | None = None, settings: Settings | None = None, openai_provider: ModelProvider | None = None) -> ModelGateway:
    """Route embeddings through the same provider-neutral gateway."""
    configured = settings or get_settings()
    if configured.model_provider == "openai":
        provider = openai_provider or OpenAIEmbeddingProvider(api_key=configured.model_api_key.get_secret_value(), base_url=configured.model_base_url) if configured.model_api_key else None
        if provider is None:
            raise ValueError("MODEL_API_KEY is required for the OpenAI embedding route.")
        return ModelGateway(session, routes={ModelTask.EMBEDDING: ModelRoute("openai", configured.embedding_model_name)}, providers={"openai": provider})
    if local_provider is None:
        raise ValueError("A local provider is required when MODEL_PROVIDER=mock.")
    return ModelGateway(session, routes={ModelTask.EMBEDDING: ModelRoute("local-demo", configured.embedding_model_name)}, providers={"local-demo": local_provider})
