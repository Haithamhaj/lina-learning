"""Construction of the configured object-storage provider."""

from services.platform.config import Settings, get_settings

from .local import LocalObjectStorage
from .models import ObjectStorage, StorageProviderUnavailable


def create_object_storage(settings: Settings | None = None) -> ObjectStorage:
    """Build the configured provider without exposing provider details."""

    settings = settings or get_settings()
    if settings.storage_provider == "local":
        signing_secret = (
            settings.session_secret.get_secret_value()
            if settings.session_secret
            else None
        )
        return LocalObjectStorage(
            settings.storage_dir,
            signing_secret=signing_secret,
        )
    if settings.storage_provider == "s3":
        raise StorageProviderUnavailable(
            "The S3-compatible provider is reserved for a later deployment task."
        )
    raise StorageProviderUnavailable(
        f"Unsupported storage provider: {settings.storage_provider}"
    )