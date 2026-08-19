"""Provider-neutral contracts for private object storage."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import BinaryIO, Mapping, Protocol, TypeAlias, runtime_checkable

StorageInput: TypeAlias = bytes | bytearray | memoryview | BinaryIO


class StorageError(RuntimeError):
    """Base error for object-storage failures."""


class InvalidStorageKey(StorageError, ValueError):
    """Raised when an object key is empty, unsafe, or not canonical."""


class ObjectNotFoundError(StorageError, FileNotFoundError):
    """Raised when an object or its metadata does not exist."""


class ObjectAlreadyExistsError(StorageError, FileExistsError):
    """Raised when storing would silently replace an existing original."""


class StorageIntegrityError(StorageError):
    """Raised when stored bytes no longer match their recorded checksum."""


class InvalidPrivateAccessToken(StorageError, ValueError):
    """Raised when a private access capability is malformed or forged."""


class ExpiredPrivateAccessToken(InvalidPrivateAccessToken):
    """Raised when a private access capability is no longer valid."""


class StorageProviderUnavailable(StorageError):
    """Raised when the selected provider is not implemented or available."""


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    """Durable metadata for one private object."""

    key: str
    content_type: str
    size: int
    checksum_sha256: str
    metadata: Mapping[str, str] = field(default_factory=dict)
    stored_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class StoredObject:
    """Object bytes together with their verified metadata."""

    content: bytes
    metadata: ObjectMetadata


@dataclass(frozen=True, slots=True)
class PrivateAccess:
    """An expiring capability, not a public URL."""

    key: str
    token: str
    expires_at: datetime


@runtime_checkable
class ObjectStorage(Protocol):
    """Contract implemented by local and future cloud providers."""

    def put(
        self,
        key: str,
        data: StorageInput,
        *,
        content_type: str = "application/octet-stream",
        metadata: Mapping[str, str] | None = None,
    ) -> ObjectMetadata:
        """Store an object and return its checksum-bearing metadata."""

    def head(self, key: str) -> ObjectMetadata:
        """Read metadata without exposing object bytes."""

    def get(self, key: str) -> StoredObject:
        """Read and integrity-check an object."""

    def delete(self, key: str) -> None:
        """Delete an object and its metadata."""

    def create_private_access(
        self,
        key: str,
        *,
        expires_in: timedelta | float = timedelta(minutes=5),
    ) -> PrivateAccess:
        """Create an expiring private capability for server-mediated reads."""

    def read_private(self, token: str) -> StoredObject:
        """Read an object using an expiring private capability."""