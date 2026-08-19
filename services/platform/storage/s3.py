"""S3-compatible private object-storage provider."""

from __future__ import annotations

import hashlib
import math
import tempfile
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Iterator, Mapping

import boto3
from botocore.exceptions import BotoCoreError, ClientError

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

_CHECKSUM_METADATA_KEY = "lina-sha256"
_CHUNK_SIZE = 1024 * 1024


class S3ObjectStorage:
    """S3-compatible implementation with private ACLs and conditional writes."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        endpoint: str | None = None,
        client: Any | None = None,
        signing_secret: str | bytes | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.bucket = bucket
        self.region = region
        self._clock = clock
        self._client = client or boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )
        self._capabilities = CapabilitySigner(signing_secret, clock=clock)

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
        user_metadata = {
            str(name).lower(): str(value) for name, value in (metadata or {}).items()
        }
        if _CHECKSUM_METADATA_KEY in user_metadata:
            raise ValueError(f"{_CHECKSUM_METADATA_KEY} is reserved by storage.")

        checksum = hashlib.sha256()
        size = 0
        with tempfile.SpooledTemporaryFile(
            max_size=8 * 1024 * 1024,
            mode="w+b",
        ) as payload:
            for chunk in self._chunks(data):
                checksum.update(chunk)
                size += len(chunk)
                payload.write(chunk)
            payload.seek(0)
            request_metadata = {
                **user_metadata,
                _CHECKSUM_METADATA_KEY: checksum.hexdigest(),
            }
            try:
                self._client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=payload,
                    ContentLength=size,
                    ContentType=content_type,
                    Metadata=request_metadata,
                    IfNoneMatch="*",
                )
            except ClientError as exc:
                if self._is_collision(exc):
                    raise ObjectAlreadyExistsError(
                        f"Refusing to replace existing object: {key}"
                    ) from exc
                raise self._provider_error("put", exc) from exc
            except BotoCoreError as exc:
                raise self._provider_error("put", exc) from exc

        return ObjectMetadata(
            key=key,
            content_type=content_type,
            size=size,
            checksum_sha256=checksum.hexdigest(),
            metadata=user_metadata,
            stored_at=datetime.fromtimestamp(self._clock(), UTC),
        )

    def head(self, key: str) -> ObjectMetadata:
        key = validate_storage_key(key)
        try:
            response = self._client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if self._is_missing(exc):
                raise ObjectNotFoundError(f"Object does not exist: {key}") from exc
            raise self._provider_error("head", exc) from exc
        except BotoCoreError as exc:
            raise self._provider_error("head", exc) from exc

        response_metadata = {
            str(name).lower(): str(value)
            for name, value in response.get("Metadata", {}).items()
        }
        checksum = response_metadata.pop(_CHECKSUM_METADATA_KEY, None)
        if not checksum:
            raise StorageIntegrityError(
                f"S3 object is missing its Lina checksum metadata: {key}"
            )
        try:
            size = int(response["ContentLength"])
        except (KeyError, TypeError, ValueError) as exc:
            raise StorageIntegrityError(f"S3 object has invalid metadata: {key}") from exc

        return ObjectMetadata(
            key=key,
            content_type=response.get("ContentType", "application/octet-stream"),
            size=size,
            checksum_sha256=checksum,
            metadata=response_metadata,
            stored_at=response.get("LastModified"),
        )

    def get(self, key: str) -> StoredObject:
        key = validate_storage_key(key)
        object_metadata = self.head(key)
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"]
            try:
                content = body.read()
            finally:
                close = getattr(body, "close", None)
                if close:
                    close()
        except ClientError as exc:
            if self._is_missing(exc):
                raise ObjectNotFoundError(f"Object does not exist: {key}") from exc
            raise self._provider_error("get", exc) from exc
        except (BotoCoreError, KeyError, TypeError) as exc:
            raise self._provider_error("get", exc) from exc

        if (
            len(content) != object_metadata.size
            or hashlib.sha256(content).hexdigest()
            != object_metadata.checksum_sha256
        ):
            raise StorageIntegrityError(f"Checksum mismatch for object: {key}")
        return StoredObject(content=content, metadata=object_metadata)

    def delete(self, key: str) -> None:
        key = validate_storage_key(key)
        self.head(key)
        try:
            self._client.delete_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            raise self._provider_error("delete", exc) from exc
        except BotoCoreError as exc:
            raise self._provider_error("delete", exc) from exc

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
        try:
            url = self._client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=max(1, math.ceil(seconds)),
            )
        except (BotoCoreError, ClientError) as exc:
            raise self._provider_error("create private access", exc) from exc
        return PrivateAccess(
            key=key,
            token=self._capabilities.issue(key, expires_at_epoch),
            expires_at=datetime.fromtimestamp(expires_at_epoch, UTC),
            url=url,
        )

    def read_private(self, token: str) -> StoredObject:
        payload = self._capabilities.verify(token)
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

    @staticmethod
    def _is_missing(exc: ClientError) -> bool:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        return code in {"404", "NoSuchKey", "NotFound"}

    @staticmethod
    def _is_collision(exc: ClientError) -> bool:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        return code in {
            "409",
            "412",
            "ConditionalRequestConflict",
            "PreconditionFailed",
        } or status in {409, 412}

    @staticmethod
    def _provider_error(operation: str, exc: BaseException) -> StorageProviderUnavailable:
        return StorageProviderUnavailable(
            f"S3-compatible storage failed during {operation}: "
            f"{exc.__class__.__name__}"
        )