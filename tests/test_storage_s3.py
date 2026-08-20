from datetime import UTC, datetime
import hashlib
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from botocore.exceptions import ClientError

from services.platform.config import Settings
from services.platform.observability import (
    STORAGE_FAILURES_TOTAL,
    StorageCounterRegistry,
)
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
        self.upload_fileobj_calls: list[dict[str, Any]] = []
        self.copy_calls: list[dict[str, Any]] = []
        self.multipart_uploads: dict[str, dict[str, Any]] = {}
        self.abort_calls: list[dict[str, str]] = []
        self.fail_upload_part_copy = False
        self.fail_upload_fileobj = False
        self.fail_delete = False
        self.fail_abort = False

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

    def upload_fileobj(
        self,
        fileobj: Any,
        bucket: str,
        key: str,
        *,
        ExtraArgs: dict[str, Any],
        Config: Any,
    ) -> None:
        self.upload_fileobj_calls.append(
            {
                "Fileobj": fileobj,
                "Bucket": bucket,
                "Key": key,
                "ExtraArgs": ExtraArgs,
                "Config": Config,
            }
        )
        content = fileobj.read()
        self.objects[key] = {
            "content": content,
            "content_type": ExtraArgs["ContentType"],
            "metadata": dict(ExtraArgs["Metadata"]),
            "stored_at": datetime.now(UTC),
            "etag": f'"{hashlib.md5(content).hexdigest()}"',
        }
        if self.fail_upload_fileobj:
            raise ClientError(
                {
                    "Error": {"Code": "InternalError"},
                    "ResponseMetadata": {"HTTPStatusCode": 500},
                },
                "UploadPart",
            )

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
        source = request["CopySource"]
        source_key = (
            source["Key"]
            if isinstance(source, dict)
            else source.rsplit("/", 1)[-1]
        )
        if source_key not in self.objects:
            raise self._missing("CopyObject")
        if request.get("IfNoneMatch") == "*" and key in self.objects:
            raise ClientError(
                {
                    "Error": {"Code": "PreconditionFailed"},
                    "ResponseMetadata": {"HTTPStatusCode": 412},
                },
                "CopyObject",
            )
        source_object = self.objects[source_key]
        if source_key == key:
            stored = source_object
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
            return
        self.objects[key] = {
            "content": source_object["content"],
            "content_type": source_object["content_type"],
            "metadata": dict(source_object["metadata"]),
            "stored_at": source_object["stored_at"],
            "etag": source_object["etag"],
        }

    def create_multipart_upload(
        self,
        *,
        Bucket: str,
        Key: str,
        ContentType: str,
        Metadata: dict[str, str],
    ) -> dict[str, str]:
        del Bucket
        upload_id = f"upload-{len(self.multipart_uploads) + 1}"
        self.multipart_uploads[upload_id] = {
            "key": Key,
            "content_type": ContentType,
            "metadata": dict(Metadata),
            "parts": {},
        }
        return {"UploadId": upload_id}

    def upload_part_copy(
        self,
        *,
        Bucket: str,
        Key: str,
        UploadId: str,
        PartNumber: int,
        CopySource: dict[str, str],
        CopySourceRange: str,
    ) -> dict[str, dict[str, str]]:
        del Bucket, Key
        if self.fail_upload_part_copy:
            raise ClientError(
                {
                    "Error": {"Code": "InternalError"},
                    "ResponseMetadata": {"HTTPStatusCode": 500},
                },
                "UploadPartCopy",
            )
        upload = self.multipart_uploads[UploadId]
        source = self.objects[CopySource["Key"]]["content"]
        start, end = (
            int(value)
            for value in CopySourceRange.removeprefix("bytes=").split("-", 1)
        )
        content = source[start : end + 1]
        upload["parts"][PartNumber] = content
        return {
            "CopyPartResult": {
                "ETag": f'"{hashlib.md5(content).hexdigest()}"',
            }
        }

    def complete_multipart_upload(
        self,
        *,
        Bucket: str,
        Key: str,
        UploadId: str,
        MultipartUpload: dict[str, list[dict[str, Any]]],
        IfNoneMatch: str,
    ) -> None:
        del Bucket
        if IfNoneMatch == "*" and Key in self.objects:
            raise ClientError(
                {
                    "Error": {"Code": "PreconditionFailed"},
                    "ResponseMetadata": {"HTTPStatusCode": 412},
                },
                "CompleteMultipartUpload",
            )
        upload = self.multipart_uploads[UploadId]
        content = b"".join(
            upload["parts"][part["PartNumber"]]
            for part in MultipartUpload["Parts"]
        )
        self.objects[Key] = {
            "content": content,
            "content_type": upload["content_type"],
            "metadata": dict(upload["metadata"]),
            "stored_at": datetime.now(UTC),
            "etag": f'"{hashlib.md5(content).hexdigest()}"',
        }
        del self.multipart_uploads[UploadId]

    def abort_multipart_upload(
        self,
        *,
        Bucket: str,
        Key: str,
        UploadId: str,
    ) -> None:
        del Bucket, Key
        self.abort_calls.append({"UploadId": UploadId})
        if self.fail_abort:
            raise ClientError(
                {
                    "Error": {"Code": "AccessDenied"},
                    "ResponseMetadata": {"HTTPStatusCode": 403},
                },
                "AbortMultipartUpload",
            )
        self.multipart_uploads.pop(UploadId, None)

    def delete_object(
        self,
        *,
        Bucket: str,
        Key: str,
        IfMatch: str | None = None,
    ) -> None:
        del Bucket
        if self.fail_delete:
            raise ClientError(
                {
                    "Error": {"Code": "AccessDenied"},
                    "ResponseMetadata": {"HTTPStatusCode": 403},
                },
                "DeleteObject",
            )
        if Key not in self.objects:
            raise self._missing("DeleteObject")
        if IfMatch is not None and self.objects[Key]["etag"] != IfMatch:
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
    metrics: StorageCounterRegistry | None = None,
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
        metrics=metrics,
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


def test_s3_large_upload_uses_multipart_transfer_and_preserves_integrity() -> None:
    fake = FakeS3Client()
    threshold = 1024 * 1024
    storage = S3ObjectStorage(
        bucket="lina-private",
        region="us-east-1",
        access_key_id="access",
        secret_access_key="secret",
        endpoint="https://s3.example.test",
        client=fake,
        signing_secret="test-secret",
        multipart_threshold=threshold,
    )
    payload = b"large in-memory payload\n" * (9 * 1024 * 1024 // 24)

    stored = storage.put(
        "books/large-book.pdf",
        payload,
        content_type="application/pdf",
        metadata={"source": "multipart-test"},
    )

    assert len(fake.upload_fileobj_calls) == 1
    transfer = fake.upload_fileobj_calls[0]
    assert transfer["Key"].startswith(".lina-multipart/")
    assert transfer["Config"].multipart_threshold == threshold
    assert transfer["ExtraArgs"]["Metadata"]["lina-sha256"] == stored.checksum_sha256
    assert storage.get(stored.key).content == payload
    assert storage.head(stored.key) == stored

    with pytest.raises(ObjectAlreadyExistsError):
        storage.put(stored.key, b"replacement" * 1024 * 1024)
    assert storage.get(stored.key).content == payload


def test_s3_default_multipart_threshold_switches_after_eight_megabytes() -> None:
    fake = FakeS3Client()
    storage = make_storage(fake)
    threshold = s3_module._DEFAULT_MULTIPART_THRESHOLD
    exact_payload = b"e" * threshold
    above_payload = b"a" * (threshold + 1)

    storage.put("books/exact-boundary.pdf", exact_payload)
    assert len(fake.put_calls) == 1
    assert fake.upload_fileobj_calls == []

    storage.put("books/above-boundary.pdf", above_payload)
    assert len(fake.upload_fileobj_calls) == 1
    assert storage.get("books/above-boundary.pdf").content == above_payload


def test_s3_large_upload_uses_multipart_copy_above_copy_object_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeS3Client()
    storage = S3ObjectStorage(
        bucket="lina-private",
        region="us-east-1",
        access_key_id="access",
        secret_access_key="secret",
        endpoint="https://s3.example.test",
        client=fake,
        signing_secret="test-secret",
        multipart_threshold=1024 * 1024,
    )
    monkeypatch.setattr(s3_module, "_COPY_OBJECT_MAX_SIZE", 1024 * 1024)
    payload = b"multipart copy payload\n" * (6 * 1024 * 1024 // 22)

    stored = storage.put("books/very-large-book.pdf", payload)

    assert fake.copy_calls == []
    assert fake.multipart_uploads == {}
    assert storage.get(stored.key).content == payload


def test_s3_multipart_copy_aborts_destination_upload_on_part_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeS3Client()
    fake.fail_upload_part_copy = True
    storage = S3ObjectStorage(
        bucket="lina-private",
        region="us-east-1",
        access_key_id="access",
        secret_access_key="secret",
        endpoint="https://s3.example.test",
        client=fake,
        signing_secret="test-secret",
        multipart_threshold=1024 * 1024,
    )
    monkeypatch.setattr(s3_module, "_COPY_OBJECT_MAX_SIZE", 1024 * 1024)
    payload = b"multipart copy failure\n" * (6 * 1024 * 1024 // 22)

    with pytest.raises(StorageProviderUnavailable, match="multipart put"):
        storage.put("books/failed-very-large-book.pdf", payload)

    assert fake.abort_calls == [{"UploadId": "upload-1"}]
    assert fake.multipart_uploads == {}


def test_s3_multipart_transfer_failure_emits_safe_counter() -> None:
    fake = FakeS3Client()
    fake.fail_upload_fileobj = True
    metrics = StorageCounterRegistry()
    storage = make_storage(fake, metrics=metrics)

    with pytest.raises(StorageProviderUnavailable, match="multipart put"):
        storage.put("student-files/private.pdf", b"x" * (9 * 1024 * 1024))

    assert metrics.snapshot() == {
        (
            STORAGE_FAILURES_TOTAL,
            "s3",
            "multipart_transfer",
            ".lina-multipart/",
        ): 1
    }


def test_s3_staging_cleanup_failure_emits_safe_counter(caplog: pytest.LogCaptureFixture) -> None:
    fake = FakeS3Client()
    fake.fail_delete = True
    metrics = StorageCounterRegistry()
    storage = make_storage(fake, metrics=metrics)

    storage.put("books/large-book.pdf", b"x" * (9 * 1024 * 1024))

    assert metrics.snapshot() == {
        (
            STORAGE_FAILURES_TOTAL,
            "s3",
            "staging_cleanup",
            ".lina-multipart/",
        ): 1
    }
    assert any(
        "storage_counter " in record.message
        and '"key_prefix":".lina-multipart/"' in record.message
        and "large-book.pdf" not in record.message
        for record in caplog.records
    )


def test_s3_destination_cleanup_failure_emits_safe_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeS3Client()
    fake.fail_upload_part_copy = True
    fake.fail_abort = True
    metrics = StorageCounterRegistry()
    storage = S3ObjectStorage(
        bucket="lina-private",
        region="us-east-1",
        access_key_id="access",
        secret_access_key="secret",
        endpoint="https://s3.example.test",
        client=fake,
        signing_secret="test-secret",
        metrics=metrics,
        multipart_threshold=1024 * 1024,
    )
    monkeypatch.setattr(s3_module, "_COPY_OBJECT_MAX_SIZE", 1024 * 1024)

    with pytest.raises(StorageProviderUnavailable, match="multipart put"):
        storage.put("student-files/large-book.pdf", b"x" * (6 * 1024 * 1024))

    assert metrics.snapshot() == {
        (
            STORAGE_FAILURES_TOTAL,
            "s3",
            "multipart_transfer",
            ".lina-multipart/",
        ): 1,
        (
            STORAGE_FAILURES_TOTAL,
            "s3",
            "destination_multipart_cleanup",
            "student-files/",
        ): 1,
    }


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