"""Private storage backed by Replit App Object Storage.

The Replit Python SDK intentionally exposes a small, provider-neutral API.  In
particular, ``upload_from_bytes`` has no GCS generation/precondition argument.
This adapter therefore uses a bounded cross-process lock and a
metadata reservation object while publishing a key.  That is safe for the
single Reserved VM deployment this provider targets, provided all writers use
this adapter.  It is not an atomic conditional-write primitive for independent
processes, workers, or bucket writers; those deployments must use the S3
provider (or a future SDK with conditional creation).

Metadata is stored in a private, hashed sidecar object because the official SDK
does not expose content type or user metadata operations.  Object bytes remain
at the caller's key and are never written to the local filesystem.  Only
ephemeral lock files under ``/tmp`` are local.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

import fcntl

from .capabilities import CapabilitySigner
from .keys import validate_storage_key
from .models import (
    ObjectAlreadyExistsError,
    ObjectMetadata,
    ObjectNotFoundError,
    PrivateAccess,
    StorageInput,
    StorageIntegrityError,
    StorageProviderUnavailable,
    StoredObject,
)

_CHUNK_SIZE = 1024 * 1024
_METADATA_PREFIX = ".lina-replit-metadata/"
_DEFAULT_LOCK_TIMEOUT = 10.0
_LOCK_ROOT = Path("/tmp/lina-replit-locks")

# The thread guard prevents same-process threads from depending on platform
# specific flock semantics. The per-key flock below protects the separate API
# and worker OS processes.
_THREAD_OPERATION_LOCK = threading.Lock()


class ReplitObjectStorage:
    """ObjectStorage implementation using the official Replit SDK.

    The SDK client is injectable for focused tests.  ``bucket_id`` is optional;
    omitted means the App Storage default bucket selected by Replit.
    """

    def __init__(
        self,
        *,
        bucket_id: str | None = None,
        signing_secret: str | bytes | None = None,
        client: Any | None = None,
        clock: Callable[[], float] = time.time,
        lock_timeout: float = _DEFAULT_LOCK_TIMEOUT,
    ) -> None:
        if bucket_id is not None and (
            not isinstance(bucket_id, str) or not bucket_id.strip()
        ):
            raise ValueError("bucket_id must be a non-empty string when provided.")
        if (
            isinstance(lock_timeout, bool)
            or not isinstance(lock_timeout, (int, float))
            or not math.isfinite(float(lock_timeout))
            or lock_timeout <= 0
        ):
            raise ValueError("lock_timeout must be a finite positive duration.")

        self._clock = clock
        self._lock_timeout = float(lock_timeout)
        self._capabilities = CapabilitySigner(signing_secret, clock=clock)
        self._sdk_not_found: tuple[type[BaseException], ...] = (ObjectNotFoundError,)

        if client is not None:
            self._client = client
            self._load_sdk_not_found_error()
            return

        try:
            from replit.object_storage import Client
            from replit.object_storage.errors import (
                ObjectNotFoundError as SDKObjectNotFoundError,
            )
        except ImportError as exc:
            raise StorageProviderUnavailable(
                "The Replit storage provider requires replit-object-storage."
            ) from exc

        self._sdk_not_found = (ObjectNotFoundError, SDKObjectNotFoundError)
        try:
            self._client = Client(bucket_id=bucket_id)
        except Exception as exc:
            raise StorageProviderUnavailable(
                "Unable to initialize Replit App Object Storage."
            ) from exc

    def _load_sdk_not_found_error(self) -> None:
        """Load the SDK exception without requiring the package for fake clients."""

        try:
            from replit.object_storage.errors import (
                ObjectNotFoundError as SDKObjectNotFoundError,
            )
        except ImportError:
            return
        self._sdk_not_found = (ObjectNotFoundError, SDKObjectNotFoundError)

    def put(
        self,
        key: str,
        data: StorageInput,
        *,
        content_type: str = "application/octet-stream",
        metadata: Mapping[str, str] | None = None,
    ) -> ObjectMetadata:
        key = validate_storage_key(key)
        if not isinstance(content_type, str) or not content_type.strip():
            raise ValueError("content_type must not be empty.")
        user_metadata = self._validate_metadata(metadata)
        content = self._read_bytes(data)
        checksum = hashlib.sha256(content).hexdigest()
        stored_at = datetime.fromtimestamp(self._clock(), UTC)
        object_metadata = ObjectMetadata(
            key=key,
            content_type=content_type,
            size=len(content),
            checksum_sha256=checksum,
            metadata=user_metadata,
            stored_at=stored_at,
        )

        # The reservation sidecar prevents readers from treating a partially
        # published object as complete and prevents a retry from replacing it.
        with self._key_lock(key):
            metadata_key = self._metadata_key(key)
            has_object = self._exists(key)
            has_metadata = self._exists(metadata_key)
            if not has_metadata:
                if has_object:
                    raise StorageIntegrityError(
                        f"Incomplete object transaction: {key}"
                    )
                self._upload(metadata_key, self._encode_reservation(object_metadata))
                self._ensure_bytes(key, content, object_metadata)
                self._upload(metadata_key, self._encode_metadata(object_metadata))
            else:
                reservation = self._download(metadata_key)
                state = self._reservation_state(reservation, key)
                if state == "complete":
                    # A complete sidecar is immutable, but a missing object
                    # means the transaction is corrupt rather than a collision.
                    if not has_object:
                        raise StorageIntegrityError(
                            f"Incomplete object transaction: {key}"
                        )
                    self._decode_metadata(reservation, key)
                    raise ObjectAlreadyExistsError(
                        f"Refusing to replace existing object: {key}"
                    )

                expected = self._decode_reservation(reservation, key)
                if not self._same_expected_object(expected, object_metadata):
                    raise ObjectAlreadyExistsError(
                        f"Refusing to replace existing object: {key}"
                    )
                self._ensure_bytes(key, content, expected)
                self._upload(metadata_key, self._encode_metadata(expected))

        return object_metadata if not has_metadata else expected

    def head(self, key: str) -> ObjectMetadata:
        key = validate_storage_key(key)
        with self._key_lock(key):
            return self._head_unlocked(key)

    def _head_unlocked(self, key: str) -> ObjectMetadata:
        metadata_key = self._metadata_key(key)
        has_object = self._exists(key)
        has_metadata = self._exists(metadata_key)
        if not has_object and not has_metadata:
            raise ObjectNotFoundError(f"Object does not exist: {key}")
        if not has_object or not has_metadata:
            raise StorageIntegrityError(f"Incomplete object transaction: {key}")
        return self._decode_metadata(self._download(metadata_key), key)

    def _ensure_bytes(
        self, key: str, content: bytes, metadata: ObjectMetadata
    ) -> None:
        """Publish bytes only when absent, and verify any bytes already present."""

        if not self._exists(key):
            self._upload(key, content)
        stored = self._download(key)
        if len(stored) != metadata.size:
            raise StorageIntegrityError(f"Size mismatch for object: {key}")
        if hashlib.sha256(stored).hexdigest() != metadata.checksum_sha256:
            raise StorageIntegrityError(f"Checksum mismatch for object: {key}")

    def get(self, key: str) -> StoredObject:
        key = validate_storage_key(key)
        with self._key_lock(key):
            object_metadata = self._head_unlocked(key)
            content = self._download(key)
            if len(content) != object_metadata.size:
                raise StorageIntegrityError(f"Size mismatch for object: {key}")
            if hashlib.sha256(content).hexdigest() != object_metadata.checksum_sha256:
                raise StorageIntegrityError(f"Checksum mismatch for object: {key}")
            return StoredObject(content=content, metadata=object_metadata)

    def delete(self, key: str) -> None:
        key = validate_storage_key(key)
        with self._key_lock(key):
            metadata_key = self._metadata_key(key)
            has_object = self._exists(key)
            has_metadata = self._exists(metadata_key)
            if not has_object and not has_metadata:
                raise ObjectNotFoundError(f"Object does not exist: {key}")
            if not has_object or not has_metadata:
                raise StorageIntegrityError(f"Incomplete object transaction: {key}")
            # Delete the bytes first: a failed metadata delete never makes
            # previously valid bytes silently become a different object.
            self._delete(key)
            self._delete(metadata_key)

    def create_private_access(
        self,
        key: str,
        *,
        expires_in: timedelta | float = timedelta(minutes=5),
    ) -> PrivateAccess:
        key = validate_storage_key(key)
        self.head(key)
        seconds = (
            expires_in.total_seconds()
            if isinstance(expires_in, timedelta)
            else float(expires_in)
        )
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("expires_in must be a finite positive duration.")
        expires_at_epoch = self._clock() + seconds
        return PrivateAccess(
            key=key,
            token=self._capabilities.issue(key, expires_at_epoch),
            expires_at=datetime.fromtimestamp(expires_at_epoch, UTC),
        )

    def read_private(self, token: str) -> StoredObject:
        payload = self._capabilities.verify(token)
        return self.get(payload["key"])

    @staticmethod
    def _read_bytes(data: StorageInput) -> bytes:
        if isinstance(data, bytes):
            return data
        if isinstance(data, (bytearray, memoryview)):
            return bytes(data)
        if not hasattr(data, "read"):
            raise TypeError("Storage data must be bytes-like or a readable stream.")
        chunks: list[bytes] = []
        while True:
            chunk = data.read(_CHUNK_SIZE)
            if not chunk:
                break
            if not isinstance(chunk, bytes):
                raise TypeError("Readable storage streams must return bytes.")
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _validate_metadata(metadata: Mapping[str, str] | None) -> dict[str, str]:
        values = dict(metadata or {})
        if any(
            not isinstance(name, str) or not isinstance(value, str)
            for name, value in values.items()
        ):
            raise TypeError("Object metadata keys and values must be strings.")
        return values

    @staticmethod
    def _metadata_key(key: str) -> str:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return f"{_METADATA_PREFIX}{digest}.json"

    @staticmethod
    def _encode_reservation(metadata: ObjectMetadata) -> bytes:
        return json.dumps(
            {
                "checksum_sha256": metadata.checksum_sha256,
                "content_type": metadata.content_type,
                "key": metadata.key,
                "metadata": dict(metadata.metadata),
                "size": metadata.size,
                "state": "reserved",
                "stored_at": (
                    metadata.stored_at.isoformat() if metadata.stored_at else None
                ),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    @staticmethod
    def _reservation_state(content: bytes, key: str) -> str:
        try:
            payload = json.loads(content.decode("utf-8"))
            state = payload["state"]
        except (UnicodeDecodeError, AttributeError, KeyError, TypeError, ValueError,
                json.JSONDecodeError) as exc:
            raise StorageIntegrityError(
                f"Invalid reservation for object: {key}"
            ) from exc
        if state not in {"reserved", "complete"}:
            raise StorageIntegrityError(f"Invalid reservation for object: {key}")
        return state

    @staticmethod
    def _decode_reservation(content: bytes, key: str) -> ObjectMetadata:
        try:
            payload = json.loads(content.decode("utf-8"))
            if payload.get("state") != "reserved":
                raise StorageIntegrityError(f"Incomplete object transaction: {key}")
            object_key = payload["key"]
            content_type = payload["content_type"]
            size = payload["size"]
            checksum = payload["checksum_sha256"]
            user_metadata = payload["metadata"]
            stored_at_value = payload["stored_at"]
            if (
                object_key != key
                or not isinstance(content_type, str)
                or not content_type.strip()
                or isinstance(size, bool)
                or not isinstance(size, int)
                or size < 0
                or not isinstance(checksum, str)
                or len(checksum) != 64
                or any(character not in "0123456789abcdef" for character in checksum)
                or not isinstance(user_metadata, dict)
                or any(
                    not isinstance(name, str) or not isinstance(value, str)
                    for name, value in user_metadata.items()
                )
                or (
                    stored_at_value is not None
                    and not isinstance(stored_at_value, str)
                )
            ):
                raise ValueError
            stored_at = (
                datetime.fromisoformat(stored_at_value)
                if stored_at_value is not None
                else None
            )
        except StorageIntegrityError:
            raise
        except (UnicodeDecodeError, AttributeError, KeyError, TypeError, ValueError,
                json.JSONDecodeError) as exc:
            raise StorageIntegrityError(
                f"Invalid reservation for object: {key}"
            ) from exc
        return ObjectMetadata(
            key=key,
            content_type=content_type,
            size=size,
            checksum_sha256=checksum,
            metadata=dict(user_metadata),
            stored_at=stored_at,
        )

    @staticmethod
    def _same_expected_object(
        expected: ObjectMetadata, incoming: ObjectMetadata
    ) -> bool:
        return (
            expected.key == incoming.key
            and expected.content_type == incoming.content_type
            and expected.size == incoming.size
            and expected.checksum_sha256 == incoming.checksum_sha256
            and dict(expected.metadata) == dict(incoming.metadata)
        )

    @staticmethod
    def _encode_metadata(metadata: ObjectMetadata) -> bytes:
        return json.dumps(
            {
                "checksum_sha256": metadata.checksum_sha256,
                "content_type": metadata.content_type,
                "key": metadata.key,
                "metadata": dict(metadata.metadata),
                "size": metadata.size,
                "state": "complete",
                "stored_at": (
                    metadata.stored_at.isoformat() if metadata.stored_at else None
                ),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    @staticmethod
    def _decode_metadata(content: bytes, key: str) -> ObjectMetadata:
        try:
            payload = json.loads(content.decode("utf-8"))
            if payload.get("state") != "complete":
                raise StorageIntegrityError(f"Incomplete object transaction: {key}")
            object_key = payload["key"]
            content_type = payload["content_type"]
            size = payload["size"]
            checksum = payload["checksum_sha256"]
            user_metadata = payload["metadata"]
            stored_at_value = payload.get("stored_at")
            if (
                object_key != key
                or not isinstance(content_type, str)
                or not content_type.strip()
                or isinstance(size, bool)
                or not isinstance(size, int)
                or size < 0
                or not isinstance(checksum, str)
                or len(checksum) != 64
                or any(character not in "0123456789abcdef" for character in checksum)
                or not isinstance(user_metadata, dict)
                or any(
                    not isinstance(name, str) or not isinstance(value, str)
                    for name, value in user_metadata.items()
                )
            ):
                raise ValueError
            stored_at = (
                datetime.fromisoformat(stored_at_value)
                if stored_at_value is not None
                else None
            )
        except StorageIntegrityError:
            raise
        except (UnicodeDecodeError, AttributeError, KeyError, TypeError, ValueError,
                json.JSONDecodeError) as exc:
            raise StorageIntegrityError(f"Invalid metadata for object: {key}") from exc
        return ObjectMetadata(
            key=key,
            content_type=content_type,
            size=size,
            checksum_sha256=checksum,
            metadata=dict(user_metadata),
            stored_at=stored_at,
        )

    def _exists(self, key: str) -> bool:
        try:
            result = self._client.exists(key)
        except self._sdk_not_found:
            return False
        except Exception as exc:
            raise StorageProviderUnavailable(
                f"Replit storage existence check failed for object: {key}"
            ) from exc
        if not isinstance(result, bool):
            raise StorageProviderUnavailable(
                f"Replit storage returned an invalid existence result for: {key}"
            )
        return result

    def _upload(self, key: str, content: bytes) -> None:
        try:
            self._client.upload_from_bytes(key, content)
        except Exception as exc:
            raise StorageProviderUnavailable(
                f"Replit storage upload failed for object: {key}"
            ) from exc

    def _download(self, key: str) -> bytes:
        try:
            content = self._client.download_as_bytes(key)
        except self._sdk_not_found as exc:
            raise ObjectNotFoundError(f"Object does not exist: {key}") from exc
        except Exception as exc:
            raise StorageProviderUnavailable(
                f"Replit storage download failed for object: {key}"
            ) from exc
        if not isinstance(content, bytes):
            raise StorageIntegrityError(
                f"Replit storage returned non-bytes content for object: {key}"
            )
        return content

    def _delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except self._sdk_not_found as exc:
            raise ObjectNotFoundError(f"Object does not exist: {key}") from exc
        except Exception as exc:
            raise StorageProviderUnavailable(
                f"Replit storage delete failed for object: {key}"
            ) from exc

    @contextmanager
    def _key_lock(self, key: str) -> Iterator[None]:
        # The lock file contains no object bytes or metadata. It is an
        # ephemeral coordination primitive on the Reserved VM only.
        with _THREAD_OPERATION_LOCK:
            _LOCK_ROOT.mkdir(parents=True, exist_ok=True)
            lock_path = _LOCK_ROOT / (
                f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.lock"
            )
            deadline = time.monotonic() + self._lock_timeout
            with lock_path.open("a+b") as lock_handle:
                while True:
                    try:
                        fcntl.flock(
                            lock_handle.fileno(),
                            fcntl.LOCK_EX | fcntl.LOCK_NB,
                        )
                        break
                    except BlockingIOError:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise ObjectAlreadyExistsError(
                                f"Another storage operation already owns key: {key}"
                            ) from None
                        time.sleep(min(0.05, remaining))
                try:
                    yield
                finally:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
