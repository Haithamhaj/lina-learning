"""Configured Model Gateway construction for application tasks."""

from __future__ import annotations

from sqlalchemy.orm import Session

from services.model_gateway.gateway import (
    ModelGateway,
    ModelProvider,
    ModelResult,
    ModelRoute,
    StaticModelProvider,
)
from services.model_gateway.openai_provider import OpenAIResponsesProvider
from services.intelligence.segment_reviews import SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION
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


def create_session_evidence_gateway(
    session: Session,
    *,
    local_provider: ModelProvider | None = None,
    settings: Settings | None = None,
    openai_provider: ModelProvider | None = None,
) -> ModelGateway:
    """Route one end-of-session evidence interpretation through the Gateway."""

    configured = settings or get_settings()
    if configured.model_provider == "openai":
        provider = openai_provider
        if provider is None:
            if configured.model_api_key is None:
                raise ValueError("MODEL_API_KEY is required for the OpenAI session evidence route.")
            provider = OpenAIResponsesProvider(
                api_key=configured.model_api_key.get_secret_value(),
                base_url=configured.model_base_url,
            )
        return ModelGateway(
            session,
            routes={ModelTask.SESSION_EVIDENCE: ModelRoute("openai", configured.model_name)},
            providers={"openai": provider},
        )

    safe_empty_provider = local_provider or StaticModelProvider(
        ModelResult(output={"version": "session-evidence-v1", "events": []})
    )
    return ModelGateway(
        session,
        routes={ModelTask.SESSION_EVIDENCE: ModelRoute("local-demo", configured.model_name)},
        providers={"local-demo": safe_empty_provider},
    )


def create_segment_evidence_gateway(
    session: Session,
    *,
    local_provider: ModelProvider | None = None,
    settings: Settings | None = None,
    openai_provider: ModelProvider | None = None,
) -> ModelGateway:
    """Route one completed-Segment semantic Review through the Gateway."""

    configured = settings or get_settings()
    if configured.model_provider == "openai":
        provider = openai_provider
        if provider is None:
            if configured.model_api_key is None:
                raise ValueError("MODEL_API_KEY is required for the OpenAI Segment Review route.")
            provider = OpenAIResponsesProvider(
                api_key=configured.model_api_key.get_secret_value(),
                base_url=configured.model_base_url,
            )
        return ModelGateway(
            session,
            routes={ModelTask.SEGMENT_EVIDENCE: ModelRoute("openai", configured.model_name)},
            providers={"openai": provider},
        )

    safe_empty_provider = local_provider or StaticModelProvider(
        ModelResult(output={"version": SEGMENT_LEARNING_REVIEW_SCHEMA_VERSION, "findings": []})
    )
    return ModelGateway(
        session,
        routes={ModelTask.SEGMENT_EVIDENCE: ModelRoute("local-demo", configured.model_name)},
        providers={"local-demo": safe_empty_provider},
    )


def create_personal_facts_gateway(
    session: Session,
    *,
    local_provider: ModelProvider | None = None,
    settings: Settings | None = None,
    openai_provider: ModelProvider | None = None,
) -> ModelGateway:
    """Route independent Personal Facts extraction through the Model Gateway."""

    configured = settings or get_settings()
    model_name = configured.personal_facts_model_name or configured.model_name
    if configured.model_provider == "openai":
        provider = openai_provider
        if provider is None:
            if configured.model_api_key is None:
                raise ValueError("MODEL_API_KEY is required for the OpenAI Personal Facts route.")
            provider = OpenAIResponsesProvider(
                api_key=configured.model_api_key.get_secret_value(),
                base_url=configured.model_base_url,
            )
        return ModelGateway(
            session,
            routes={ModelTask.PERSONAL_FACTS: ModelRoute("openai", model_name)},
            providers={"openai": provider},
        )

    safe_empty_provider = local_provider or StaticModelProvider(
        ModelResult(output={"version": "personal-facts-extraction-v1", "candidates": []})
    )
    return ModelGateway(
        session,
        routes={ModelTask.PERSONAL_FACTS: ModelRoute("local-demo", model_name)},
        providers={"local-demo": safe_empty_provider},
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
