"""S3-compatible private object storage."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import math
import secrets
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Iterator, Mapping
from urllib.parse import urlparse

from botocore.exceptions import BotoCoreError, ClientError

from .keys import validate_storage_key
from .models import (
    ExpiredPrivateAccessToken,
    InvalidPrivateAccessToken,
    ObjectAlreadyExistsError,
    ObjectMetadata,
    ObjectNotFoundError,
    PrivateAccess,
    StorageInput,
    StorageIntegrityError,
    StorageProviderUnavailable,
    StoredObject,
)

_TOKEN_VERSION = "v1"
_CHUNK_SIZE = 1024 * 1024
_SPOOL_MAX_SIZE = 8 * 1024 * 1024
# Lina-namespaced S3 user-metadata keys.
_CHECKSUM_METADATA_KEY = "lina-sha256"
_STORED_AT_METADATA_KEY = "lina-stored-at"
_OBJECT_METADATA_KEY = "lina-metadata"
# HMAC-SHA256 over the canonical metadata bundle, preventing tampered metadata
# from passing a byte-only integrity check.
_INTEGRITY_HMAC_KEY = "lina-hmac"
_INTERNAL_METADATA_KEYS = {
    _CHECKSUM_METADATA_KEY,
    _STORED_AT_METADATA_KEY,
    _OBJECT_METADATA_KEY,
    _INTEGRITY_HMAC_KEY,
}
_COPYABLE_HEAD_PROPERTIES = (
    "CacheControl",
    "ContentDisposition",
    "ContentEncoding",
    "ContentLanguage",
    "Expires",
    "WebsiteRedirectLocation",
    "StorageClass",
    "ServerSideEncryption",
    "SSEKMSKeyId",
    "SSEKMSEncryptionContext",
    "BucketKeyEnabled",
    "ObjectLockMode",
    "ObjectLockRetainUntilDate",
    "ObjectLockLegalHoldStatus",
)


@dataclass(frozen=True, slots=True)
class MetadataRotationReport:
    """Counts from one S3 metadata-signature rotation run."""

    scanned: int
    resigned: int
    already_rotated: int


def _canonical_bundle(
    key: str,
    content_type: str,
    size: int,
    checksum_hex: str,
    stored_at_iso: str,
    user_metadata: dict[str, str],
) -> bytes:
    """Stable canonical representation of the complete metadata bundle."""

    document = json.dumps(
        {
            "checksum_sha256": checksum_hex,
            "content_type": content_type,
            "key": key,
            "metadata": dict(sorted(user_metadata.items())),
            "size": size,
            "stored_at": stored_at_iso,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return document.encode("utf-8")


class S3ObjectStorage:
    """Private S3-compatible storage with immutable original keys.

    The provider never creates public URLs. Private access is an application
    capability signed with the configured session secret, then resolved through
    the server-side S3 client.

    Object metadata is authenticated with an HMAC-SHA256 over a canonical
    bundle that includes key, content type, size, stored-at timestamp, SHA-256
    checksum, and caller-supplied metadata. Reading any object whose bundle
    signature is absent or invalid raises StorageIntegrityError so a bucket-
    level writer cannot forge metadata that passes bytes-only verification.
    """

    def __init__(
        self,
        bucket: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        *,
        endpoint: str | None = None,
        signing_secret: str | bytes | None = None,
        client: Any | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not bucket.strip():
            raise ValueError("S3 bucket must not be empty.")
        if not region.strip():
            raise ValueError("S3 region must not be empty.")
        if not access_key_id.strip() or not secret_access_key.strip():
            raise ValueError("S3 access credentials must not be empty.")

        self.bucket = bucket
        self.region = region
        self.endpoint = endpoint
        self._clock = clock
        if isinstance(signing_secret, str):
            signing_secret = signing_secret.encode("utf-8")
        self._signing_secret = signing_secret or secrets.token_bytes(32)

        # Accept an injected client (for tests with a fake/moto client).
        # When building a real client, validate the endpoint transport security.
        if client is not None:
            self._client = client
        else:
            if endpoint is not None:
                self._validate_endpoint(endpoint)
            self._client = self._build_client(
                endpoint=endpoint,
                region=region,
                access_key_id=access_key_id,
                secret_access_key=secret_access_key,
            )

    @staticmethod
    def _validate_endpoint(endpoint: str) -> None:
        """Reject non-HTTPS endpoints to prevent credential/data exposure."""

        parsed = urlparse(endpoint)
        if parsed.scheme != "https":
            raise ValueError(
                f"S3_ENDPOINT must use HTTPS to protect credentials and private "
                f"objects in transit (got scheme '{parsed.scheme}'). "
                f"For local development with a fake/moto client, pass the client "
                f"directly via the 'client' parameter instead of setting endpoint."
            )
        if parsed.username or parsed.password:
            raise ValueError(
                "S3_ENDPOINT must not embed credentials in the URL."
            )

    @staticmethod
    def _build_client(
        *,
        endpoint: str | None,
        region: str,
        access_key_id: str,
        secret_access_key: str,
    ) -> Any:
        try:
            import boto3
        except ImportError as exc:
            raise StorageProviderUnavailable(
                "The S3 provider requires the boto3 package."
            ) from exc

        client_options: dict[str, str] = {
            "service_name": "s3",
            "region_name": region,
            "aws_access_key_id": access_key_id,
            "aws_secret_access_key": secret_access_key,
        }
        if endpoint:
            client_options["endpoint_url"] = endpoint
        try:
            return boto3.client(**client_options)
        except (BotoCoreError, ClientError) as exc:
            raise StorageProviderUnavailable(
                "Unable to initialize the configured S3 provider."
            ) from exc

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

        checksum = hashlib.sha256()
        size = 0
        stored_at = datetime.fromtimestamp(self._clock(), UTC)
        stored_at_iso = stored_at.isoformat()
        with tempfile.SpooledTemporaryFile(
            max_size=_SPOOL_MAX_SIZE,
            mode="w+b",
        ) as payload:
            for chunk in self._chunks(data):
                checksum.update(chunk)
                size += len(chunk)
                payload.write(chunk)
            checksum_hex = checksum.hexdigest()

            # Build and sign the canonical metadata bundle so that future reads
            # can prove the bytes and metadata belong to the same write.
            bundle = _canonical_bundle(
                key, content_type, size, checksum_hex, stored_at_iso, user_metadata
            )
            bundle_hmac = self._sign_bytes(bundle)

            transport_metadata: dict[str, str] = {}
            transport_metadata.update(user_metadata)
            transport_metadata[_CHECKSUM_METADATA_KEY] = checksum_hex
            transport_metadata[_STORED_AT_METADATA_KEY] = stored_at_iso
            # S3 lowercases user-metadata keys. Keep an encoded copy so the
            # provider can return the caller's metadata exactly as supplied.
            transport_metadata[_OBJECT_METADATA_KEY] = json.dumps(
                user_metadata,
                separators=(",", ":"),
                sort_keys=True,
            )
            transport_metadata[_INTEGRITY_HMAC_KEY] = bundle_hmac

            payload.seek(0)
            try:
                self._client.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=payload,
                    ContentType=content_type,
                    Metadata=transport_metadata,
                    IfNoneMatch="*",
                )
            except ClientError as exc:
                if self._is_collision(exc):
                    raise ObjectAlreadyExistsError(
                        f"Refusing to replace existing object: {key}"
                    ) from exc
                self._raise_provider_error("put", key, exc)
            except BotoCoreError as exc:
                raise StorageProviderUnavailable(
                    f"S3 put failed for object: {key}"
                ) from exc

        return ObjectMetadata(
            key=key,
            content_type=content_type,
            size=size,
            checksum_sha256=checksum_hex,
            metadata=user_metadata,
            stored_at=stored_at,
        )

    def resign_metadata(
        self,
        *,
        old_signing_secret: str | bytes,
        new_signing_secret: str | bytes,
        prefix: str | None = None,
        dry_run: bool = False,
    ) -> MetadataRotationReport:
        """Re-sign every object metadata bundle without changing object bytes.

        The complete inventory is verified with the old secret before the first
        metadata copy is attempted. If a previous run already updated an
        object, its new signature is accepted so an interrupted run can resume
        safely. Any object that verifies with neither secret aborts the run.
        """

        old_secret = self._require_signing_secret(
            old_signing_secret,
            label="old_signing_secret",
        )
        new_secret = self._require_signing_secret(
            new_signing_secret,
            label="new_signing_secret",
        )
        if hmac.compare_digest(old_secret, new_secret):
            raise ValueError("old_signing_secret and new_signing_secret must differ.")
        if prefix is not None and not isinstance(prefix, str):
            raise TypeError("prefix must be a string when provided.")

        verified: list[tuple[str, ObjectMetadata, Mapping[str, Any]]] = []
        already_rotated = 0
        for key in self._list_object_keys(prefix=prefix):
            response = self._head_response(key)
            try:
                metadata = self._metadata_from_head_response(
                    key,
                    response,
                    signing_secret=old_secret,
                )
            except StorageIntegrityError as old_error:
                # This branch makes a partially completed rotation resumable.
                # It does not permit tampered objects: the new HMAC must also
                # authenticate the exact current metadata bundle.
                try:
                    self._metadata_from_head_response(
                        key,
                        response,
                        signing_secret=new_secret,
                    )
                except StorageIntegrityError:
                    raise old_error
                already_rotated += 1
                continue

            etag = response.get("ETag")
            if not isinstance(etag, str) or not etag:
                raise StorageProviderUnavailable(
                    f"S3 metadata rotation requires an ETag for object: {key}"
                )
            self._validate_copy_properties(key, response)
            verified.append((key, metadata, response))

        if dry_run:
            return MetadataRotationReport(
                scanned=len(verified) + already_rotated,
                resigned=0,
                already_rotated=already_rotated,
            )

        for key, metadata, response in verified:
            bundle = _canonical_bundle(
                metadata.key,
                metadata.content_type,
                metadata.size,
                metadata.checksum_sha256,
                metadata.stored_at.isoformat() if metadata.stored_at else "",
                dict(metadata.metadata),
            )
            self._replace_metadata(
                key,
                metadata,
                response=response,
                bundle_hmac=self._sign_bytes(bundle, signing_secret=new_secret),
            )

        return MetadataRotationReport(
            scanned=len(verified) + already_rotated,
            resigned=len(verified),
            already_rotated=already_rotated,
        )

    def _list_object_keys(self, *, prefix: str | None) -> Iterator[str]:
        continuation_token: str | None = None
        while True:
            request: dict[str, Any] = {
                "Bucket": self.bucket,
                "MaxKeys": 1000,
            }
            if prefix is not None:
                request["Prefix"] = prefix
            if continuation_token is not None:
                request["ContinuationToken"] = continuation_token

            try:
                response = self._client.list_objects_v2(**request)
            except ClientError as exc:
                self._raise_provider_error("list", prefix or "*", exc)
            except BotoCoreError as exc:
                raise StorageProviderUnavailable(
                    "S3 object listing failed during metadata rotation."
                ) from exc

            contents = response.get("Contents") or []
            if not isinstance(contents, list):
                raise StorageProviderUnavailable(
                    "S3 returned an invalid object listing during metadata rotation."
                )
            for entry in contents:
                if not isinstance(entry, Mapping):
                    raise StorageProviderUnavailable(
                        "S3 returned an invalid object entry during metadata rotation."
                    )
                object_key = entry.get("Key")
                if not isinstance(object_key, str):
                    raise StorageProviderUnavailable(
                        "S3 returned an object without a valid key during metadata rotation."
                    )
                yield validate_storage_key(object_key)

            if not response.get("IsTruncated"):
                return
            next_token = response.get("NextContinuationToken")
            if not isinstance(next_token, str) or not next_token:
                raise StorageProviderUnavailable(
                    "S3 returned a truncated listing without a continuation token."
                )
            continuation_token = next_token

    def _head_response(self, key: str) -> Mapping[str, Any]:
        try:
            response = self._client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            self._raise_not_found_or_provider_error("head", key, exc)
        except BotoCoreError as exc:
            raise StorageProviderUnavailable(
                f"S3 head failed for object: {key}"
            ) from exc
        if not isinstance(response, Mapping):
            raise StorageProviderUnavailable(
                f"S3 returned an invalid head response for object: {key}"
            )
        return response

    def _replace_metadata(
        self,
        key: str,
        metadata: ObjectMetadata,
        *,
        response: Mapping[str, Any],
        bundle_hmac: str,
    ) -> None:
        transport_metadata = dict(metadata.metadata)
        transport_metadata[_CHECKSUM_METADATA_KEY] = metadata.checksum_sha256
        transport_metadata[_STORED_AT_METADATA_KEY] = (
            metadata.stored_at.isoformat() if metadata.stored_at else ""
        )
        transport_metadata[_OBJECT_METADATA_KEY] = json.dumps(
            dict(metadata.metadata),
            separators=(",", ":"),
            sort_keys=True,
        )
        transport_metadata[_INTEGRITY_HMAC_KEY] = bundle_hmac
        request: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": key,
            "CopySource": {"Bucket": self.bucket, "Key": key},
            "CopySourceIfMatch": response["ETag"],
            "MetadataDirective": "REPLACE",
            "ContentType": metadata.content_type,
            "Metadata": transport_metadata,
            # MetadataDirective=REPLACE otherwise resets object tags.
            "TaggingDirective": "COPY",
        }
        for property_name in _COPYABLE_HEAD_PROPERTIES:
            value = response.get(property_name)
            if value is not None:
                request[property_name] = value
        try:
            self._client.copy_object(**request)
        except ClientError as exc:
            if self._is_collision(exc):
                raise StorageProviderUnavailable(
                    f"S3 object changed while rotating metadata: {key}"
                ) from exc
            self._raise_provider_error("metadata rotation", key, exc)
        except BotoCoreError as exc:
            raise StorageProviderUnavailable(
                f"S3 metadata rotation failed for object: {key}"
            ) from exc

    @staticmethod
    def _validate_copy_properties(
        key: str,
        response: Mapping[str, Any],
    ) -> None:
        # SSE-C keys are never returned by HeadObject and must not be copied
        # without the customer's encryption key. Refuse rather than silently
        # re-encrypting or making an inaccessible object.
        if response.get("SSECustomerAlgorithm") or response.get(
            "SSECustomerKeyMD5"
        ):
            raise StorageProviderUnavailable(
                "S3 metadata rotation cannot copy SSE-C object without its "
                f"encryption key: {key}"
            )

    def head(self, key: str) -> ObjectMetadata:
        key = validate_storage_key(key)
        response = self._head_response(key)
        return self._metadata_from_head_response(key, response)

    def get(self, key: str) -> StoredObject:
        key = validate_storage_key(key)
        object_metadata = self.head(key)
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"]
            if isinstance(body, bytes):
                content = body
            elif hasattr(body, "read"):
                content = body.read()
            else:
                raise StorageIntegrityError(
                    f"S3 returned an unreadable body for object: {key}"
                )
            if hasattr(body, "close"):
                body.close()
        except KeyError as exc:
            raise StorageIntegrityError(
                f"S3 returned an incomplete response for object: {key}"
            ) from exc
        except ClientError as exc:
            self._raise_not_found_or_provider_error("get", key, exc)
        except BotoCoreError as exc:
            raise StorageProviderUnavailable(
                f"S3 get failed for object: {key}"
            ) from exc

        if not isinstance(content, bytes):
            raise StorageIntegrityError(
                f"S3 returned a non-bytes body for object: {key}"
            )
        if len(content) != object_metadata.size:
            raise StorageIntegrityError(f"Size mismatch for object: {key}")
        if hashlib.sha256(content).hexdigest() != object_metadata.checksum_sha256:
            raise StorageIntegrityError(f"Checksum mismatch for object: {key}")
        return StoredObject(content=content, metadata=object_metadata)

    def delete(self, key: str) -> None:
        key = validate_storage_key(key)
        # DeleteObject is idempotent in S3, while this contract reports a
        # missing object. Read and validate the current ETag first, then use
        # IfMatch so a delayed delete cannot remove a newly uploaded original.
        try:
            response = self._client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            self._raise_not_found_or_provider_error("head", key, exc)
        except BotoCoreError as exc:
            raise StorageProviderUnavailable(
                f"S3 head failed for object: {key}"
            ) from exc

        self._metadata_from_head_response(key, response)
        etag = response.get("ETag")
        if not isinstance(etag, str) or not etag:
            raise StorageProviderUnavailable(
                f"S3 delete requires an ETag for object: {key}"
            )
        try:
            self._client.delete_object(
                Bucket=self.bucket,
                Key=key,
                IfMatch=etag,
            )
        except ClientError as exc:
            if self._is_collision(exc):
                raise ObjectAlreadyExistsError(
                    f"Object changed while deleting: {key}"
                ) from exc
            self._raise_not_found_or_provider_error("delete", key, exc)
        except BotoCoreError as exc:
            raise StorageProviderUnavailable(
                f"S3 delete failed for object: {key}"
            ) from exc

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
        token = f"{_TOKEN_VERSION}.{payload}.{self._sign(payload)}"
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

    @staticmethod
    def _validate_metadata(metadata: Mapping[str, str] | None) -> dict[str, str]:
        values = dict(metadata or {})
        if any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in values.items()
        ):
            raise TypeError("Object metadata keys and values must be strings.")
        if any(key.lower() in _INTERNAL_METADATA_KEYS for key in values):
            raise ValueError("Metadata uses a reserved Lina storage key.")
        return values

    def _metadata_from_head_response(
        self,
        key: str,
        response: Mapping[str, Any],
        *,
        signing_secret: bytes | None = None,
    ) -> ObjectMetadata:
        raw_metadata = {
            str(name).lower(): str(value)
            for name, value in dict(response.get("Metadata") or {}).items()
        }

        # --- checksum ---
        checksum = raw_metadata.get(_CHECKSUM_METADATA_KEY)
        if not checksum:
            encoded_checksum = response.get("ChecksumSHA256")
            if encoded_checksum:
                try:
                    checksum = base64.b64decode(
                        encoded_checksum,
                        validate=True,
                    ).hex()
                except (binascii.Error, ValueError):
                    checksum = None
        if (
            not checksum
            or len(checksum) != hashlib.sha256().digest_size * 2
            or any(character not in "0123456789abcdef" for character in checksum)
        ):
            raise StorageIntegrityError(
                f"S3 object is missing a valid SHA-256 checksum: {key}"
            )

        # --- caller metadata ---
        encoded_metadata = raw_metadata.get(_OBJECT_METADATA_KEY)
        if encoded_metadata is not None:
            try:
                user_metadata = json.loads(encoded_metadata)
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise StorageIntegrityError(
                    f"S3 object has invalid metadata: {key}"
                ) from exc
            if not isinstance(user_metadata, dict) or any(
                not isinstance(name, str) or not isinstance(value, str)
                for name, value in user_metadata.items()
            ):
                raise StorageIntegrityError(f"S3 object has invalid metadata: {key}")
        else:
            user_metadata = {
                name: value
                for name, value in raw_metadata.items()
                if name not in _INTERNAL_METADATA_KEYS
            }

        # --- stored_at ---
        stored_at_value = raw_metadata.get(_STORED_AT_METADATA_KEY)
        if stored_at_value is not None:
            try:
                stored_at = (
                    None
                    if stored_at_value == ""
                    else datetime.fromisoformat(stored_at_value)
                )
            except ValueError as exc:
                raise StorageIntegrityError(
                    f"S3 object has invalid stored timestamp: {key}"
                ) from exc
        else:
            stored_at = response.get("LastModified")
            if stored_at is not None and stored_at.tzinfo is None:
                stored_at = stored_at.replace(tzinfo=UTC)

        # --- size / content_type ---
        try:
            size = int(response["ContentLength"])
        except (KeyError, TypeError, ValueError) as exc:
            raise StorageIntegrityError(
                f"S3 object has invalid content length: {key}"
            ) from exc
        content_type = response.get("ContentType") or "application/octet-stream"
        if size < 0 or not isinstance(content_type, str):
            raise StorageIntegrityError(f"S3 object has invalid metadata: {key}")

        # --- integrity HMAC ---
        # Verify that the canonical bundle matches the signature written at put
        # time.  An absent or invalid signature means a bucket-level writer may
        # have tampered with metadata; either way we cannot trust the object.
        stored_at_iso = stored_at.isoformat() if stored_at is not None else ""
        expected_bundle = _canonical_bundle(
            key, content_type, size, checksum, stored_at_iso, user_metadata
        )
        stored_hmac = raw_metadata.get(_INTEGRITY_HMAC_KEY)
        expected_hmac = self._sign_bytes(
            expected_bundle,
            signing_secret=signing_secret,
        )
        if stored_hmac is None or not hmac.compare_digest(stored_hmac, expected_hmac):
            raise StorageIntegrityError(
                f"Metadata integrity check failed for object: {key}"
            )

        return ObjectMetadata(
            key=key,
            content_type=content_type,
            size=size,
            checksum_sha256=checksum,
            metadata=user_metadata,
            stored_at=stored_at,
        )

    @staticmethod
    def _is_collision(error: ClientError) -> bool:
        code = str(error.response.get("Error", {}).get("Code", ""))
        status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        return code in {
            "409",
            "412",
            "ConditionalRequestConflict",
            "PreconditionFailed",
        } or status in {409, 412}

    @staticmethod
    def _is_not_found(error: ClientError) -> bool:
        code = str(error.response.get("Error", {}).get("Code", ""))
        status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        return (
            code in {"404", "NoSuchKey", "NoSuchObject", "NotFound"}
            or status == 404
        )

    @classmethod
    def _raise_not_found_or_provider_error(
        cls,
        operation: str,
        key: str,
        error: ClientError,
    ) -> None:
        if cls._is_not_found(error):
            raise ObjectNotFoundError(f"Object does not exist: {key}") from error
        cls._raise_provider_error(operation, key, error)

    @staticmethod
    def _raise_provider_error(
        operation: str,
        key: str,
        error: ClientError,
    ) -> None:
        code = str(error.response.get("Error", {}).get("Code", "unknown"))
        raise StorageProviderUnavailable(
            f"S3 {operation} failed for object {key} ({code})."
        ) from error

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
            if (
                not isinstance(key, str)
                or not isinstance(expires, (int, float))
                or isinstance(expires, bool)
                or not math.isfinite(float(expires))
            ):
                raise ValueError
            validate_storage_key(key)
            return {"key": key, "exp": expires}
        except (
            AttributeError,
            binascii.Error,
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            raise InvalidPrivateAccessToken(
                "Private access token is invalid."
            ) from None

    def _sign(self, payload: str) -> str:
        return self._sign_bytes(payload.encode("ascii"))

    @staticmethod
    def _require_signing_secret(
        signing_secret: str | bytes,
        *,
        label: str,
    ) -> bytes:
        if isinstance(signing_secret, str):
            signing_secret = signing_secret.encode("utf-8")
        if not isinstance(signing_secret, bytes) or not signing_secret:
            raise ValueError(f"{label} must be a non-empty string or bytes value.")
        return signing_secret

    def _sign_bytes(
        self,
        data: bytes,
        *,
        signing_secret: bytes | None = None,
    ) -> str:
        digest = hmac.new(
            signing_secret or self._signing_secret,
            data,
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
