"""Filesystem-backed private object storage for development and tests."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import secrets
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping

from .models import (
    ExpiredPrivateAccessToken,
    InvalidPrivateAccessToken,
    InvalidStorageKey,
    ObjectAlreadyExistsError,
    ObjectMetadata,
    ObjectNotFoundError,
    PrivateAccess,
    StorageInput,
    StorageIntegrityError,
    StoredObject,
)

_TOKEN_VERSION = "v1"
_CHUNK_SIZE = 1024 * 1024


def validate_storage_key(key: str) -> str:
    """Return a canonical relative key or reject path traversal."""

    if not isinstance(key, str) or not key:
        raise InvalidStorageKey("Storage keys must be non-empty strings.")
    if "\x00" in key or "\\" in key or key.startswith("/"):
        raise InvalidStorageKey("Storage keys must use safe relative POSIX paths.")

    path = PurePosixPath(key)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise InvalidStorageKey(
            "Storage keys cannot be absolute, normalized, or traverse directories."
        )
    canonical = "/".join(path.parts)
    if canonical != key:
        raise InvalidStorageKey("Storage keys must be canonical POSIX paths.")
    return canonical


class LocalObjectStorage:
    """Private filesystem storage with signed, expiring read capabilities."""

    def __init__(
        self,
        root: Path,
        *,
        signing_secret: str | bytes | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        if isinstance(signing_secret, str):
            signing_secret = signing_secret.encode("utf-8")
        self._signing_secret = signing_secret or secrets.token_bytes(32)
        self._clock = clock

    def put(
        self,
        key: str,
        data: StorageInput,
        *,
        content_type: str = "application/octet-stream",
        metadata: Mapping[str, str] | None = None,
    ) -> ObjectMetadata:
        key = validate_storage_key(key)
        if not content_type.strip():
            raise ValueError("content_type must not be empty.")
        object_path = self._object_path(key)
        if object_path.exists() or self._metadata_path(object_path).exists():
            raise ObjectAlreadyExistsError(
                f"Refusing to replace existing object: {key}"
            )
        object_path.parent.mkdir(parents=True, exist_ok=True)
        checksum = hashlib.sha256()
        size = 0
        moved_object = False
        temporary_object: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                dir=object_path.parent,
                prefix=f".{object_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_object = Path(handle.name)
                for chunk in self._chunks(data):
                    checksum.update(chunk)
                    size += len(chunk)
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(temporary_object, object_path)
            moved_object = True
            temporary_object = None
            object_metadata = ObjectMetadata(
                key=key,
                content_type=content_type,
                size=size,
                checksum_sha256=checksum.hexdigest(),
                metadata=dict(metadata or {}),
                stored_at=datetime.fromtimestamp(self._clock(), UTC),
            )
            self._write_metadata(object_path, object_metadata)
            return object_metadata
        except Exception:
            if temporary_object is not None:
                temporary_object.unlink(missing_ok=True)
            if moved_object:
                object_path.unlink(missing_ok=True)
                self._metadata_path(object_path).unlink(missing_ok=True)
            raise

    def head(self, key: str) -> ObjectMetadata:
        key = validate_storage_key(key)
        object_path = self._object_path(key)
        metadata_path = self._metadata_path(object_path)
        if not object_path.is_file() or not metadata_path.is_file():
            raise ObjectNotFoundError(f"Object does not exist: {key}")

        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            object_metadata = ObjectMetadata(
                key=payload["key"],
                content_type=payload["content_type"],
                size=int(payload["size"]),
                checksum_sha256=payload["checksum_sha256"],
                metadata=dict(payload.get("metadata", {})),
                stored_at=(
                    datetime.fromisoformat(payload["stored_at"])
                    if payload.get("stored_at")
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise StorageIntegrityError(f"Invalid metadata for object: {key}") from exc

        if object_metadata.key != key or object_metadata.size != object_path.stat().st_size:
            raise StorageIntegrityError(f"Metadata does not match object: {key}")
        return object_metadata

    def get(self, key: str) -> StoredObject:
        key = validate_storage_key(key)
        object_metadata = self.head(key)
        content = self._object_path(key).read_bytes()
        checksum = hashlib.sha256(content).hexdigest()
        if checksum != object_metadata.checksum_sha256:
            raise StorageIntegrityError(f"Checksum mismatch for object: {key}")
        return StoredObject(content=content, metadata=object_metadata)

    def delete(self, key: str) -> None:
        key = validate_storage_key(key)
        object_path = self._object_path(key)
        metadata_path = self._metadata_path(object_path)
        if not object_path.exists() and not metadata_path.exists():
            raise ObjectNotFoundError(f"Object does not exist: {key}")
        object_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        self._remove_empty_parents(object_path.parent)

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
        payload = self._encode_payload({"key": key, "exp": expires_at_epoch})
        signature = self._sign(payload)
        token = f"{_TOKEN_VERSION}.{payload}.{signature}"
        return PrivateAccess(
            key=key,
            token=token,
            expires_at=datetime.fromtimestamp(expires_at_epoch, UTC),
        )

    def read_private(self, token: str) -> StoredObject:
        payload = self._decode_token(token)
        if self._clock() >= float(payload["exp"]):
            raise ExpiredPrivateAccessToken("Private access has expired.")
        return self.get(payload["key"])

    @staticmethod
    def _chunks(data: StorageInput):
        if isinstance(data, bytes):
            yield data
            return
        if isinstance(data, (bytearray, memoryview)):
            yield bytes(data)
            return
        if not hasattr(data, "read"):
            raise TypeError("Storage data must be bytes-like or a readable stream.")
        while True:
            chunk = data.read(_CHUNK_SIZE)
            if not chunk:
                break
            if not isinstance(chunk, bytes):
                raise TypeError("Readable storage streams must return bytes.")
            yield chunk

    def _object_path(self, key: str) -> Path:
        path = self.root.joinpath(*key.split("/"))
        resolved_root = self.root.resolve()
        try:
            path.resolve().relative_to(resolved_root)
        except ValueError as exc:
            raise InvalidStorageKey("Storage key escapes the configured root.") from exc
        return path

    @staticmethod
    def _metadata_path(object_path: Path) -> Path:
        return object_path.with_name(f"{object_path.name}.metadata.json")

    def _write_metadata(
        self,
        object_path: Path,
        object_metadata: ObjectMetadata,
    ) -> None:
        metadata_path = self._metadata_path(object_path)
        payload = {
            "key": object_metadata.key,
            "content_type": object_metadata.content_type,
            "size": object_metadata.size,
            "checksum_sha256": object_metadata.checksum_sha256,
            "metadata": dict(object_metadata.metadata),
            "stored_at": (
                object_metadata.stored_at.isoformat()
                if object_metadata.stored_at
                else None
            ),
        }
        temporary_metadata: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=metadata_path.parent,
                prefix=f".{metadata_path.name}.",
                suffix=".tmp",
                mode="w",
                encoding="utf-8",
                delete=False,
            ) as handle:
                temporary_metadata = Path(handle.name)
                json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_metadata, metadata_path)
        finally:
            if temporary_metadata is not None:
                temporary_metadata.unlink(missing_ok=True)

    def _remove_empty_parents(self, parent: Path) -> None:
        resolved_root = self.root.resolve()
        while parent.resolve() != resolved_root:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    def _encode_payload(self, payload: dict[str, object]) -> str:
        encoded = json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return self._base64url(encoded)

    def _decode_token(self, token: str) -> dict[str, object]:
        try:
            version, encoded_payload, signature = token.split(".", 2)
            if version != _TOKEN_VERSION:
                raise ValueError
            if not hmac.compare_digest(signature, self._sign(encoded_payload)):
                raise ValueError
            payload = json.loads(self._from_base64url(encoded_payload))
            key = payload["key"]
            expires = payload["exp"]
            if not isinstance(key, str) or not isinstance(expires, (int, float)):
                raise ValueError
            validate_storage_key(key)
            return {"key": key, "exp": expires}
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise InvalidPrivateAccessToken("Private access token is invalid.") from None

    def _sign(self, payload: str) -> str:
        digest = hmac.new(
            self._signing_secret,
            payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return self._base64url(digest)

    @staticmethod
    def _base64url(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @staticmethod
    def _from_base64url(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)