"""Construction of the configured object-storage provider."""

from services.platform.config import Settings, get_settings

from .local import LocalObjectStorage
from .models import ObjectStorage, StorageProviderUnavailable
from .s3 import S3ObjectStorage


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
        if (
            settings.s3_bucket is None
            or settings.s3_region is None
            or settings.s3_access_key_id is None
            or settings.s3_secret_access_key is None
        ):
            raise StorageProviderUnavailable(
                "S3-compatible storage requires a complete validated configuration."
            )
        return S3ObjectStorage(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            endpoint=settings.s3_endpoint,
            access_key_id=settings.s3_access_key_id.get_secret_value(),
            secret_access_key=settings.s3_secret_access_key.get_secret_value(),
            signing_secret=(
                settings.session_secret.get_secret_value()
                if settings.session_secret
                else None
            ),
        )
    raise StorageProviderUnavailable(
        f"Unsupported storage provider: {settings.storage_provider}"
    )