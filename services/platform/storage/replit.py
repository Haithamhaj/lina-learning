"""Private Replit App Storage adapter for a single Reserved VM deployment.

The official Replit client stores bytes only: it has no object metadata or
conditional-create operation.  Lina therefore keeps an HMAC-authenticated
private sidecar for each object and coordinates API/worker writers with a
per-key lock on the one Reserved VM.  This provider is deliberately not a
multi-VM implementation; use the S3 provider when a deployment needs an
object-store-enforced conditional write.
"""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import math
import secrets
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

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
_LOCK_ROOT = Path("/tmp/lina-replit-storage-locks")
_METADATA_PREFIX = ".lina-replit-metadata/"


class ReplitObjectStorage:
    """Store private, immutable objects in the Replit App Storage bucket."""

    def __init__(
        self,
        *,
        bucket_id: str | None = None,
        signing_secret: str | bytes | None = None,
        client: Any | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if bucket_id is not None and (not isinstance(bucket_id, str) or not bucket_id.strip()):
            raise ValueError("bucket_id must be a non-empty string when provided.")
        if isinstance(signing_secret, str):
            signing_secret = signing_secret.encode("utf-8")
        self._signing_secret = signing_secret or secrets.token_bytes(32)
        self._clock = clock
        self._capabilities = CapabilitySigner(self._signing_secret, clock=clock)
        self._not_found_errors: tuple[type[BaseException], ...] = (ObjectNotFoundError,)
        if client is not None:
            self._client = client
            self._load_sdk_errors()
            return
        try:
            from replit.object_storage import Client
            from replit.object_storage.errors import ObjectNotFoundError as ReplitNotFound
        except ImportError as exc:
            raise StorageProviderUnavailable(
                "The Replit storage provider requires replit-object-storage."
            ) from exc
        self._not_found_errors = (ObjectNotFoundError, ReplitNotFound)
        try:
            self._client = Client(bucket_id=bucket_id)
        except Exception as exc:
            raise StorageProviderUnavailable("Unable to initialize Replit App Storage.") from exc

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
        expected = ObjectMetadata(
            key=key,
            content_type=content_type,
            size=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            metadata=user_metadata,
            stored_at=datetime.fromtimestamp(self._clock(), UTC),
        )

        with self._key_lock(key):
            sidecar = self._metadata_key(key)
            object_exists = self._exists(key)
            sidecar_exists = self._exists(sidecar)
            if sidecar_exists:
                recorded = self._decode_record(self._download(sidecar), key)
                if recorded["state"] == "complete":
                    if not object_exists:
                        raise StorageIntegrityError(f"Incomplete object transaction: {key}")
                    raise ObjectAlreadyExistsError(f"Refusing to replace existing object: {key}")
                reserved = self._metadata_from_record(recorded, key)
                if not self._same_object(reserved, expected):
                    raise ObjectAlreadyExistsError(f"Refusing to replace existing object: {key}")
                self._publish_bytes(key, content, reserved, object_exists)
                self._upload(sidecar, self._encode_record(reserved, "complete"))
                return reserved
            if object_exists:
                raise StorageIntegrityError(f"Incomplete object transaction: {key}")

            self._upload(sidecar, self._encode_record(expected, "reserved"))
            self._publish_bytes(key, content, expected, False)
            self._upload(sidecar, self._encode_record(expected, "complete"))
            return expected

    def head(self, key: str) -> ObjectMetadata:
        key = validate_storage_key(key)
        with self._key_lock(key):
            return self._head_unlocked(key)

    def get(self, key: str) -> StoredObject:
        key = validate_storage_key(key)
        with self._key_lock(key):
            metadata = self._head_unlocked(key)
            content = self._download(key)
            self._verify_bytes(key, content, metadata)
            return StoredObject(content=content, metadata=metadata)

    def delete(self, key: str) -> None:
        key = validate_storage_key(key)
        with self._key_lock(key):
            self._head_unlocked(key)
            self._delete(key)
            self._delete(self._metadata_key(key))

    def create_private_access(
        self, key: str, *, expires_in: timedelta | float = timedelta(minutes=5)
    ) -> PrivateAccess:
        key = validate_storage_key(key)
        self.head(key)
        seconds = expires_in.total_seconds() if isinstance(expires_in, timedelta) else float(expires_in)
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("expires_in must be a finite positive duration.")
        expires_at = self._clock() + seconds
        return PrivateAccess(
            key=key,
            token=self._capabilities.issue(key, expires_at),
            expires_at=datetime.fromtimestamp(expires_at, UTC),
        )

    def read_private(self, token: str) -> StoredObject:
        return self.get(self._capabilities.verify(token)["key"])

    def _head_unlocked(self, key: str) -> ObjectMetadata:
        sidecar = self._metadata_key(key)
        if not self._exists(key) and not self._exists(sidecar):
            raise ObjectNotFoundError(f"Object does not exist: {key}")
        if not self._exists(key) or not self._exists(sidecar):
            raise StorageIntegrityError(f"Incomplete object transaction: {key}")
        record = self._decode_record(self._download(sidecar), key)
        if record["state"] != "complete":
            raise StorageIntegrityError(f"Incomplete object transaction: {key}")
        return self._metadata_from_record(record, key)

    def _publish_bytes(
        self, key: str, content: bytes, metadata: ObjectMetadata, exists: bool
    ) -> None:
        if not exists:
            self._upload(key, content)
        self._verify_bytes(key, self._download(key), metadata)

    @staticmethod
    def _same_object(left: ObjectMetadata, right: ObjectMetadata) -> bool:
        return (
            left.key == right.key
            and left.content_type == right.content_type
            and left.size == right.size
            and left.checksum_sha256 == right.checksum_sha256
            and dict(left.metadata) == dict(right.metadata)
        )

    @staticmethod
    def _verify_bytes(key: str, content: bytes, metadata: ObjectMetadata) -> None:
        if len(content) != metadata.size or hashlib.sha256(content).hexdigest() != metadata.checksum_sha256:
            raise StorageIntegrityError(f"Checksum mismatch for object: {key}")

    def _encode_record(self, metadata: ObjectMetadata, state: str) -> bytes:
        payload = {
            "checksum_sha256": metadata.checksum_sha256,
            "content_type": metadata.content_type,
            "key": metadata.key,
            "metadata": dict(sorted(metadata.metadata.items())),
            "size": metadata.size,
            "state": state,
            "stored_at": metadata.stored_at.isoformat() if metadata.stored_at else None,
        }
        signed = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload["signature"] = hmac.new(self._signing_secret, signed, hashlib.sha256).hexdigest()
        return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    def _decode_record(self, content: bytes, key: str) -> dict[str, Any]:
        try:
            payload = json.loads(content.decode("utf-8"))
            signature = payload.pop("signature")
            canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
            expected = hmac.new(self._signing_secret, canonical, hashlib.sha256).hexdigest()
            if not isinstance(signature, str) or not hmac.compare_digest(signature, expected):
                raise ValueError("invalid signature")
            if payload.get("key") != key or payload.get("state") not in {"reserved", "complete"}:
                raise ValueError("invalid object record")
            return payload
        except (UnicodeDecodeError, AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise StorageIntegrityError(f"Invalid metadata for object: {key}") from exc

    @staticmethod
    def _metadata_from_record(record: Mapping[str, Any], key: str) -> ObjectMetadata:
        try:
            content_type = record["content_type"]
            size = record["size"]
            checksum = record["checksum_sha256"]
            user_metadata = record["metadata"]
            stored_at = record["stored_at"]
            if (
                not isinstance(content_type, str)
                or not content_type.strip()
                or isinstance(size, bool)
                or not isinstance(size, int)
                or size < 0
                or not isinstance(checksum, str)
                or len(checksum) != 64
                or any(character not in "0123456789abcdef" for character in checksum)
                or not isinstance(user_metadata, dict)
                or any(not isinstance(name, str) or not isinstance(value, str) for name, value in user_metadata.items())
                or not isinstance(stored_at, str)
            ):
                raise ValueError
            return ObjectMetadata(
                key=key,
                content_type=content_type,
                size=size,
                checksum_sha256=checksum,
                metadata=dict(user_metadata),
                stored_at=datetime.fromisoformat(stored_at),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise StorageIntegrityError(f"Invalid metadata for object: {key}") from exc

    @staticmethod
    def _read_bytes(data: StorageInput) -> bytes:
        if isinstance(data, bytes):
            return data
        if isinstance(data, (bytearray, memoryview)):
            return bytes(data)
        if not hasattr(data, "read"):
            raise TypeError("Storage data must be bytes-like or a readable stream.")
        chunks: list[bytes] = []
        while chunk := data.read(_CHUNK_SIZE):
            if not isinstance(chunk, bytes):
                raise TypeError("Readable storage streams must return bytes.")
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def _validate_metadata(metadata: Mapping[str, str] | None) -> dict[str, str]:
        values = dict(metadata or {})
        if any(not isinstance(name, str) or not isinstance(value, str) for name, value in values.items()):
            raise TypeError("Object metadata keys and values must be strings.")
        return values

    @staticmethod
    def _metadata_key(key: str) -> str:
        return f"{_METADATA_PREFIX}{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"

    def _load_sdk_errors(self) -> None:
        try:
            from replit.object_storage.errors import ObjectNotFoundError as ReplitNotFound
        except ImportError:
            return
        self._not_found_errors = (ObjectNotFoundError, ReplitNotFound)

    def _exists(self, key: str) -> bool:
        try:
            result = self._client.exists(key)
        except self._not_found_errors:
            return False
        except Exception as exc:
            raise StorageProviderUnavailable(f"Replit storage existence check failed for object: {key}") from exc
        if not isinstance(result, bool):
            raise StorageProviderUnavailable(f"Replit storage returned an invalid existence result for: {key}")
        return result

    def _upload(self, key: str, content: bytes) -> None:
        try:
            self._client.upload_from_bytes(key, content)
        except Exception as exc:
            raise StorageProviderUnavailable(f"Replit storage upload failed for object: {key}") from exc

    def _download(self, key: str) -> bytes:
        try:
            content = self._client.download_as_bytes(key)
        except self._not_found_errors as exc:
            raise ObjectNotFoundError(f"Object does not exist: {key}") from exc
        except Exception as exc:
            raise StorageProviderUnavailable(f"Replit storage download failed for object: {key}") from exc
        if not isinstance(content, bytes):
            raise StorageIntegrityError(f"Replit storage returned non-bytes content for object: {key}")
        return content

    def _delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except self._not_found_errors as exc:
            raise ObjectNotFoundError(f"Object does not exist: {key}") from exc
        except Exception as exc:
            raise StorageProviderUnavailable(f"Replit storage delete failed for object: {key}") from exc

    @contextmanager
    def _key_lock(self, key: str) -> Iterator[None]:
        _LOCK_ROOT.mkdir(parents=True, exist_ok=True)
        lock_path = _LOCK_ROOT / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.lock"
        with lock_path.open("a+b") as lock_handle:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
