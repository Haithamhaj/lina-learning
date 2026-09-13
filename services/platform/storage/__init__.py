"""Private object-storage contracts and configured providers."""

from .factory import create_object_storage
from .keys import validate_storage_key
from .local import LocalObjectStorage
from .models import (
    ExpiredPrivateAccessToken,
    InvalidPrivateAccessToken,
    InvalidStorageKey,
    ObjectAlreadyExistsError,
    ObjectMetadata,
    ObjectNotFoundError,
    ObjectStorage,
    PrivateAccess,
    StorageError,
    StorageIntegrityError,
    StorageProviderUnavailable,
    StoredObject,
)
from .replit import ReplitObjectStorage
from .s3 import MetadataRotationReport, S3ObjectStorage

__all__ = [
    "ExpiredPrivateAccessToken",
    "InvalidPrivateAccessToken",
    "InvalidStorageKey",
    "LocalObjectStorage",
    "MetadataRotationReport",
    "ObjectAlreadyExistsError",
    "ObjectMetadata",
    "ObjectNotFoundError",
    "ObjectStorage",
    "PrivateAccess",
    "ReplitObjectStorage",
    "StorageError",
    "StorageIntegrityError",
    "StorageProviderUnavailable",
    "S3ObjectStorage",
    "StoredObject",
    "create_object_storage",
    "validate_storage_key",
]