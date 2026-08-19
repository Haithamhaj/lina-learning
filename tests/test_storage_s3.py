from datetime import UTC, datetime
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
    create_object_storage,
)
from services.platform.storage import s3 as s3_module


class FakeS3Client:
    """Small in-memory S3 surface for contract tests without network access."""

    def __init__(self) -> None:
        self.objects: dict[str, dict[str, Any]] = {}
        self.put_calls: list[dict[str, Any]] = []

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
        }

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        del Bucket
        if Key not in self.objects:
            raise self._missing("HeadObject")
        stored = self.objects[Key]
        return {
            "ContentLength": len(stored["content"]),
            "ContentType": stored["content_type"],
            "Metadata": dict(stored["metadata"]),
            "LastModified": stored["stored_at"],
        }

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        del Bucket
        if Key not in self.objects:
            raise self._missing("GetObject")
        stored = self.objects[Key]
        return {"Body": BytesIO(stored["content"])}

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        del Bucket
        if Key not in self.objects:
            raise self._missing("DeleteObject")
        del self.objects[Key]

    def generate_presigned_url(
        self,
        *,
        ClientMethod: str,
        Params: dict[str, str],
        ExpiresIn: int,
    ) -> str:
        assert ClientMethod == "get_object"
        return (
            f"https://s3.example.test/{Params['Bucket']}/{Params['Key']}"
            f"?expires={ExpiresIn}"
        )

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
    assert access.url == (
        "https://s3.example.test/lina-private/books/grade-5-math.pdf?expires=60"
    )
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


def test_storage_factory_selects_s3_without_network(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake = FakeS3Client()
    monkeypatch.setattr(s3_module.boto3, "client", lambda *args, **kwargs: fake)
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