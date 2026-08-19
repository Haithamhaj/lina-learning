from datetime import UTC, datetime
import hashlib
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from botocore.exceptions import ClientError

from services.platform.config import Settings
from services.platform.storage import (
    ExpiredPrivateAccessToken,
    ObjectAlreadyExistsError,
    ObjectNotFoundError,
    S3ObjectStorage,
    StorageIntegrityError,
    StorageProviderUnavailable,
    create_object_storage,
)
from services.platform.storage import s3 as s3_module


class FakeS3Client:
    """Small in-memory S3 surface for contract tests without network access."""

    def __init__(self) -> None:
        self.objects: dict[str, dict[str, Any]] = {}
        self.put_calls: list[dict[str, Any]] = []
        self.copy_calls: list[dict[str, Any]] = []

    def put_object(self, **request: Any) -> None:
        self.put_calls.append(request)
        key = request["Key"]
        if key in self.objects:
            raise ClientError(
                {
                    "Error": {"Code": "PreconditionFailed"},
                    "ResponseMetadata": {"HTTPStatusCode": 412},
                },
                "PutObject",
            )
        body = request["Body"]
        content = body.read() if hasattr(body, "read") else body
        self.objects[key] = {
            "content": content,
            "content_type": request["ContentType"],
            "metadata": dict(request["Metadata"]),
            "stored_at": datetime.now(UTC),
            "etag": f'"{hashlib.md5(content).hexdigest()}"',
        }

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        del Bucket
        if Key not in self.objects:
            raise self._missing("HeadObject")
        stored = self.objects[Key]
        response = {
            "ContentLength": len(stored["content"]),
            "ContentType": stored["content_type"],
            "Metadata": dict(stored["metadata"]),
            "LastModified": stored["stored_at"],
            "ETag": stored["etag"],
        }
        response.update(stored.get("properties", {}))
        return response

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        del Bucket
        if Key not in self.objects:
            raise self._missing("GetObject")
        stored = self.objects[Key]
        return {"Body": BytesIO(stored["content"])}

    def list_objects_v2(self, **request: Any) -> dict[str, Any]:
        del request["Bucket"], request["MaxKeys"]
        prefix = request.get("Prefix")
        keys = sorted(
            key
            for key in self.objects
            if prefix is None or key.startswith(prefix)
        )
        return {"Contents": [{"Key": key} for key in keys], "IsTruncated": False}

    def copy_object(self, **request: Any) -> None:
        self.copy_calls.append(request)
        key = request["Key"]
        if key not in self.objects:
            raise self._missing("CopyObject")
        stored = self.objects[key]
        if stored["etag"] != request["CopySourceIfMatch"]:
            raise ClientError(
                {
                    "Error": {"Code": "PreconditionFailed"},
                    "ResponseMetadata": {"HTTPStatusCode": 412},
                },
                "CopyObject",
            )
        stored["metadata"] = dict(request["Metadata"])
        stored["content_type"] = request["ContentType"]

    def delete_object(self, *, Bucket: str, Key: str, IfMatch: str) -> None:
        del Bucket
        if Key not in self.objects:
            raise self._missing("DeleteObject")
        if self.objects[Key]["etag"] != IfMatch:
            raise ClientError(
                {
                    "Error": {"Code": "PreconditionFailed"},
                    "ResponseMetadata": {"HTTPStatusCode": 412},
                },
                "DeleteObject",
            )
        del self.objects[Key]

    @staticmethod
    def _missing(operation: str) -> ClientError:
        return ClientError(
            {
                "Error": {"Code": "NoSuchKey"},
                "ResponseMetadata": {"HTTPStatusCode": 404},
            },
            operation,
        )


def make_storage(
    fake: FakeS3Client,
    *,
    clock=lambda: 1000.0,
) -> S3ObjectStorage:
    return S3ObjectStorage(
        bucket="lina-private",
        region="us-east-1",
        access_key_id="access",
        secret_access_key="secret",
        endpoint="https://s3.example.test",
        client=fake,
        signing_secret="test-secret",
        clock=clock,
    )


def test_s3_round_trip_preserves_checksum_metadata_and_private_access() -> None:
    fake = FakeS3Client()
    storage = make_storage(fake)

    stored = storage.put(
        "books/grade-5-math.pdf",
        b"original book bytes",
        content_type="application/pdf",
        metadata={"source": "fixture"},
    )

    assert stored.size == len(b"original book bytes")
    assert storage.get(stored.key).content == b"original book bytes"
    assert storage.head(stored.key).metadata == {"source": "fixture"}
    assert fake.put_calls[0]["IfNoneMatch"] == "*"

    access = storage.create_private_access(stored.key, expires_in=60)
    assert access.url is None
    assert "://" not in access.token
    assert storage.read_private(access.token).content == b"original book bytes"

    with pytest.raises(ObjectAlreadyExistsError):
        storage.put(stored.key, b"replacement")


def test_s3_private_access_expires_and_missing_objects_are_clear() -> None:
    fake = FakeS3Client()
    now = [1000.0]
    storage = make_storage(fake, clock=lambda: now[0])
    storage.put("student-images/work.jpg", b"student original")

    access = storage.create_private_access("student-images/work.jpg", expires_in=5)
    now[0] = 1005.0
    with pytest.raises(ExpiredPrivateAccessToken):
        storage.read_private(access.token)

    storage.delete("student-images/work.jpg")
    with pytest.raises(ObjectNotFoundError):
        storage.get("student-images/work.jpg")


def test_s3_integrity_check_rejects_changed_remote_bytes() -> None:
    fake = FakeS3Client()
    storage = make_storage(fake)
    storage.put("documents/file.txt", b"original")
    fake.objects["documents/file.txt"]["content"] = b"changed"

    with pytest.raises(StorageIntegrityError):
        storage.get("documents/file.txt")


def test_s3_metadata_hmac_rotation_preserves_readability_and_bytes() -> None:
    fake = FakeS3Client()
    old_storage = make_storage(fake)
    old_storage.put(
        "student-files/work.pdf",
        b"student original bytes",
        content_type="application/pdf",
        metadata={"owner": "student"},
    )
    original_bytes = fake.objects["student-files/work.pdf"]["content"]

    assert old_storage.get("student-files/work.pdf").content == original_bytes

    new_storage = S3ObjectStorage(
        bucket="lina-private",
        region="us-east-1",
        access_key_id="access",
        secret_access_key="secret",
        endpoint="https://s3.example.test",
        client=fake,
        signing_secret="new-test-secret",
    )
    with pytest.raises(StorageIntegrityError):
        new_storage.get("student-files/work.pdf")

    report = old_storage.resign_metadata(
        old_signing_secret="test-secret",
        new_signing_secret="new-test-secret",
    )

    assert report.scanned == 1
    assert report.resigned == 1
    assert report.already_rotated == 0
    assert len(fake.copy_calls) == 1
    assert fake.objects["student-files/work.pdf"]["content"] == original_bytes
    assert new_storage.get("student-files/work.pdf").content == original_bytes
    access = new_storage.create_private_access("student-files/work.pdf")
    assert new_storage.read_private(access.token).content == original_bytes


def test_s3_metadata_hmac_rotation_preserves_copyable_head_properties() -> None:
    fake = FakeS3Client()
    storage = make_storage(fake)
    storage.put("student-files/work.pdf", b"student original bytes")
    fake.objects["student-files/work.pdf"]["properties"] = {
        "CacheControl": "private, max-age=60",
        "ContentDisposition": "attachment; filename=work.pdf",
        "ContentEncoding": "gzip",
        "ContentLanguage": "en",
        "Expires": datetime(2030, 1, 1, tzinfo=UTC),
        "WebsiteRedirectLocation": "/not-used",
        "StorageClass": "STANDARD",
        "ServerSideEncryption": "aws:kms",
        "SSEKMSKeyId": "arn:aws:kms:us-east-1:123456789012:key/example",
        "SSEKMSEncryptionContext": "eyJwdXJwb3NlIjoic3R1ZGVudCJ9",
        "BucketKeyEnabled": True,
        "ObjectLockMode": "GOVERNANCE",
        "ObjectLockRetainUntilDate": datetime(2030, 1, 1, tzinfo=UTC),
        "ObjectLockLegalHoldStatus": "OFF",
    }

    storage.resign_metadata(
        old_signing_secret="test-secret",
        new_signing_secret="new-test-secret",
    )

    request = fake.copy_calls[0]
    assert request["TaggingDirective"] == "COPY"
    for name, value in fake.objects["student-files/work.pdf"]["properties"].items():
        assert request[name] == value


def test_s3_metadata_hmac_rotation_refuses_customer_key_encryption() -> None:
    fake = FakeS3Client()
    storage = make_storage(fake)
    storage.put("student-files/work.pdf", b"student original bytes")
    fake.objects["student-files/work.pdf"]["properties"] = {
        "SSECustomerAlgorithm": "AES256",
    }

    with pytest.raises(StorageProviderUnavailable, match="SSE-C"):
        storage.resign_metadata(
            old_signing_secret="test-secret",
            new_signing_secret="new-test-secret",
        )

    assert fake.copy_calls == []


def test_s3_metadata_hmac_rotation_rejects_tampering_before_writes() -> None:
    fake = FakeS3Client()
    storage = make_storage(fake)
    storage.put("student-files/good.txt", b"good")
    storage.put("student-files/tampered.txt", b"tampered")
    fake.objects["student-files/tampered.txt"]["metadata"]["lina-hmac"] = "forged"

    with pytest.raises(StorageIntegrityError):
        storage.resign_metadata(
            old_signing_secret="test-secret",
            new_signing_secret="new-test-secret",
        )

    assert fake.copy_calls == []


def test_storage_factory_selects_s3_without_network(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake = FakeS3Client()
    monkeypatch.setattr(
        s3_module.S3ObjectStorage,
        "_build_client",
        staticmethod(lambda **_: fake),
    )
    settings = Settings(
        _env_file=None,
        storage_provider="s3",
        storage_dir=tmp_path,
        s3_bucket="bucket",
        s3_region="region",
        s3_endpoint="https://s3.example.test",
        s3_access_key_id="access",
        s3_secret_access_key="secret",
    )

    storage = create_object_storage(settings)

    assert isinstance(storage, S3ObjectStorage)
    storage.put("fixture.bin", b"fixture")