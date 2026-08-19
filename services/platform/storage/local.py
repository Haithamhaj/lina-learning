"""Filesystem-backed private object storage for development and tests."""

from __future__ import annotations

import base64
import fcntl
import hashlib
import hmac
import json
import math
import os
import secrets
import shutil
import tempfile
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Callable, Iterator, Mapping

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
    if not path.parts or path.parts[0] == ".locks":
        raise InvalidStorageKey("The .locks namespace is reserved by storage.")
    canonical = "/".join(path.parts)
    if canonical != key:
        raise InvalidStorageKey("Storage keys must be canonical POSIX paths.")
    return canonical


class LocalObjectStorage:
    """Private filesystem storage with atomic collision-safe publishing."""

    def __init__(
        self,
        root: Path,
        *,
        signing_secret: str | bytes | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.root = Path(root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock_root = self.root / ".locks"
        self._lock_root.mkdir(parents=True, exist_ok=True)
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
        object_path.parent.mkdir(parents=True, exist_ok=True)
        with self._key_lock(key):
            self._recover_abandoned_transactions(object_path)
            if object_path.exists():
                raise ObjectAlreadyExistsError(
                    f"Refusing to replace existing object: {key}"
                )

            checksum = hashlib.sha256()
            size = 0
            transaction_path: Path | None = Path(
                tempfile.mkdtemp(
                    dir=object_path.parent,
                    prefix=f".{object_path.name}.txn-",
                )
            )
            try:
                data_path = transaction_path / "data"
                with data_path.open("wb") as handle:
                    for chunk in self._chunks(data):
                        checksum.update(chunk)
                        size += len(chunk)
                        handle.write(chunk)
                    handle.flush()
                    os.fsync(handle.fileno())

                object_metadata = ObjectMetadata(
                    key=key,
                    content_type=content_type,
                    size=size,
                    checksum_sha256=checksum.hexdigest(),
                    metadata=dict(metadata or {}),
                    stored_at=datetime.fromtimestamp(self._clock(), UTC),
                )
                self._write_metadata(transaction_path / "metadata.json", object_metadata)

                # The object is a directory containing both bytes and metadata.
                # Renaming the completed transaction directory publishes both
                # atomically; readers never observe a half-published object.
                os.replace(transaction_path, object_path)
                self._fsync_directory(object_path.parent)
                transaction_path = None
                return object_metadata
            finally:
                if transaction_path is not None:
                    shutil.rmtree(transaction_path, ignore_errors=True)

    def head(self, key: str) -> ObjectMetadata:
        key = validate_storage_key(key)
        object_path = self._object_path(key)
        if not object_path.is_dir():
            raise ObjectNotFoundError(f"Object does not exist: {key}")

        data_path = object_path / "data"
        metadata_path = object_path / "metadata.json"
        if not data_path.is_file() or not metadata_path.is_file():
            raise StorageIntegrityError(f"Incomplete object transaction: {key}")

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

        if object_metadata.key != key or object_metadata.size != data_path.stat().st_size:
            raise StorageIntegrityError(f"Metadata does not match object: {key}")
        return object_metadata

    def get(self, key: str) -> StoredObject:
        key = validate_storage_key(key)
        object_metadata = self.head(key)
        content = (self._object_path(key) / "data").read_bytes()
        checksum = hashlib.sha256(content).hexdigest()
        if checksum != object_metadata.checksum_sha256:
            raise StorageIntegrityError(f"Checksum mismatch for object: {key}")
        return StoredObject(content=content, metadata=object_metadata)

    def delete(self, key: str) -> None:
        key = validate_storage_key(key)
        object_path = self._object_path(key)
        with self._key_lock(key):
            if not object_path.is_dir():
                raise ObjectNotFoundError(f"Object does not exist: {key}")
            shutil.rmtree(object_path)
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
    def _chunks(data: StorageInput) -> Iterator[bytes]:
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
        key_parts = key.split("/")
        object_path = self.root.joinpath(
            *key_parts[:-1],
            f"{key_parts[-1]}.object",
        )
        resolved_root = self.root.resolve()
        try:
            object_path.resolve().relative_to(resolved_root)
        except ValueError as exc:
            raise InvalidStorageKey("Storage key escapes the configured root.") from exc
        return object_path

    def _lock_path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._lock_root / f"{digest}.lock"

    @contextmanager
    def _key_lock(self, key: str):
        lock_path = self._lock_path(key)
        with lock_path.open("a+b") as lock_handle:
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ObjectAlreadyExistsError(
                    f"Another storage operation already owns key: {key}"
                ) from exc
            try:
                yield
            finally:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)

    def _recover_abandoned_transactions(self, object_path: Path) -> None:
        pattern = f".{object_path.name}.txn-*"
        for transaction_path in object_path.parent.glob(pattern):
            if transaction_path.is_dir():
                shutil.rmtree(transaction_path, ignore_errors=True)

    @staticmethod
    def _write_metadata(
        metadata_path: Path,
        object_metadata: ObjectMetadata,
    ) -> None:
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
        with metadata_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, separators=(",", ":"), sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        directory_fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

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