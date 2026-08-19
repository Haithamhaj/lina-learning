from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
from threading import Barrier

from botocore.exceptions import ClientError
import pytest

from services.platform.config import Settings
from services.platform.storage import (
    ExpiredPrivateAccessToken,
    InvalidPrivateAccessToken,
    InvalidStorageKey,
    LocalObjectStorage,
    ObjectAlreadyExistsError,
    ObjectNotFoundError,
    S3ObjectStorage,
    StorageIntegrityError,
    create_object_storage,
)


class FakeS3Client:
    """Small in-memory S3 surface for provider integration tests."""

    def __init__(self) -> None:
        self.objects: dict[str, dict[str, object]] = {}

    @staticmethod
    def _error(code: str, status: int) -> ClientError:
        return ClientError(
            {
                "Error": {"Code": code},
                "ResponseMetadata": {"HTTPStatusCode": status},
            },
            "S3 test operation",
        )

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body,
        ContentType: str,
        Metadata,
        IfNoneMatch: str,
    ):
        del Bucket
        if IfNoneMatch == "*" and Key in self.objects:
            raise self._error("PreconditionFailed", 412)
        content = Body.read() if hasattr(Body, "read") else Body
        self.objects[Key] = {
            "content": content,
            "content_type": ContentType,
            "metadata": dict(Metadata),
            "etag": f'"{hashlib.md5(content).hexdigest()}"',
        }

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        del Bucket
        try:
            stored = self.objects[Key]
        except KeyError:
            raise self._error("NoSuchKey", 404) from None
        return {
            "ContentLength": len(stored["content"]),
            "ContentType": stored["content_type"],
            "Metadata": dict(stored["metadata"]),
            "ETag": stored["etag"],
        }

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        del Bucket
        try:
            content = self.objects[Key]["content"]
        except KeyError:
            raise self._error("NoSuchKey", 404) from None
        return {"Body": BytesIO(content)}

    def delete_object(self, *, Bucket: str, Key: str, IfMatch: str) -> None:
        del Bucket
        if Key not in self.objects:
            raise self._error("NoSuchKey", 404)
        if self.objects[Key]["etag"] != IfMatch:
            raise self._error("PreconditionFailed", 412)
        del self.objects[Key]


def make_s3_storage(
    client: FakeS3Client | None = None,
    *,
    clock=lambda: 1000.0,
) -> S3ObjectStorage:
    return S3ObjectStorage(
        "private-bucket",
        "us-east-1",
        "access",
        "secret",
        signing_secret="test-secret",
        client=client if client is not None else FakeS3Client(),
        clock=clock,
    )


def test_local_storage_preserves_bytes_metadata_and_checksum(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path / "private", signing_secret="test-secret")
    original = b"original book bytes"

    stored = storage.put(
        "books/grade-5-math.pdf",
        BytesIO(original),
        content_type="application/pdf",
        metadata={"source": "fixture", "kind": "original"},
    )

    assert stored.key == "books/grade-5-math.pdf"
    assert stored.content_type == "application/pdf"
    assert stored.size == len(original)
    assert len(stored.checksum_sha256) == 64
    assert storage.head(stored.key) == stored
    read_back = storage.get(stored.key)
    assert read_back.content == original
    assert read_back.metadata.checksum_sha256 == stored.checksum_sha256
    assert read_back.metadata.metadata == {
        "source": "fixture",
        "kind": "original",
    }


def test_private_access_is_expiring_and_not_a_public_url(tmp_path: Path) -> None:
    now = [1000.0]
    storage = LocalObjectStorage(
        tmp_path / "private",
        signing_secret="test-secret",
        clock=lambda: now[0],
    )
    storage.put("student-images/work.jpg", b"student original")

    access = storage.create_private_access("student-images/work.jpg", expires_in=60)
    assert access.token.startswith("v1.")
    assert "://" not in access.token
    assert storage.read_private(access.token).content == b"student original"

    now[0] = 1060.0
    with pytest.raises(ExpiredPrivateAccessToken):
        storage.read_private(access.token)


def test_private_access_rejects_tampering(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path / "private", signing_secret="test-secret")
    storage.put("private/file.txt", b"content")
    token = storage.create_private_access("private/file.txt").token

    with pytest.raises(InvalidPrivateAccessToken):
        storage.read_private(f"{token}x")


def test_local_storage_rejects_unsafe_keys(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path / "private", signing_secret="test-secret")

    for key in (
        "",
        ".",
        "../outside.txt",
        "nested/../../outside",
        "/absolute",
        "bad\\key",
        ".locks/reserved",
    ):
        with pytest.raises(InvalidStorageKey):
            storage.put(key, b"not allowed")

    assert not (tmp_path / "outside.txt").exists()


def test_delete_removes_object_and_metadata(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path / "private", signing_secret="test-secret")
    storage.put("documents/file.txt", b"content")

    storage.delete("documents/file.txt")

    with pytest.raises(ObjectNotFoundError):
        storage.get("documents/file.txt")
    assert not storage._object_path("documents/file.txt").exists()


def test_put_does_not_replace_an_existing_original(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path / "private", signing_secret="test-secret")
    storage.put("documents/original.txt", b"first version")

    with pytest.raises(ObjectAlreadyExistsError):
        storage.put("documents/original.txt", b"replacement")

    assert storage.get("documents/original.txt").content == b"first version"


def test_corrupt_bytes_fail_integrity_check(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path / "private", signing_secret="test-secret")
    storage.put("documents/file.txt", b"content")
    (storage._object_path("documents/file.txt") / "data").write_bytes(b"changed")

    with pytest.raises(StorageIntegrityError):
        storage.get("documents/file.txt")


def test_concurrent_same_key_has_one_winner_and_no_mixed_metadata(
    tmp_path: Path,
) -> None:
    root = tmp_path / "private"
    stores = [
        LocalObjectStorage(root, signing_secret="test-secret"),
        LocalObjectStorage(root, signing_secret="test-secret"),
    ]
    barrier = Barrier(2)
    candidates = (
        (b"first original", "first"),
        (b"second original", "second"),
    )

    def upload(
        index: int,
    ) -> tuple[str, bytes | None]:
        content, label = candidates[index]
        barrier.wait()
        try:
            stores[index].put(
                "books/concurrent.pdf",
                content,
                content_type="application/pdf",
                metadata={"writer": label},
            )
            return label, content
        except ObjectAlreadyExistsError:
            return label, None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(upload, range(2)))

    winners = [(label, content) for label, content in results if content is not None]
    assert len(winners) == 1
    winning_label, winning_content = winners[0]
    stored = stores[0].get("books/concurrent.pdf")
    assert stored.content == winning_content
    assert stored.metadata.metadata == {"writer": winning_label}


def test_storage_factory_defaults_to_local(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, storage_dir=tmp_path / "configured")

    storage = create_object_storage(settings)

    assert isinstance(storage, LocalObjectStorage)
    storage.put("fixture.bin", b"fixture")


def test_storage_factory_selects_s3_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeS3Client()
    settings = Settings(
        _env_file=None,
        storage_provider="s3",
        s3_bucket="bucket",
        s3_region="region",
        s3_access_key_id="access",
        s3_secret_access_key="secret",
    )
    monkeypatch.setattr("boto3.client", lambda **_: fake_client)
    storage = create_object_storage(settings)

    assert isinstance(storage, S3ObjectStorage)
    storage.put("fixture.bin", b"fixture")
    assert storage.get("fixture.bin").content == b"fixture"


def test_s3_storage_preserves_bytes_metadata_and_checksum() -> None:
    storage = make_s3_storage()
    stored = storage.put(
        "books/grade-5-math.pdf",
        BytesIO(b"original book bytes"),
        content_type="application/pdf",
        metadata={"Source": "fixture", "kind": "original"},
    )

    assert stored.size == len(b"original book bytes")
    assert storage.head(stored.key) == stored
    read_back = storage.get(stored.key)
    assert read_back.content == b"original book bytes"
    assert read_back.metadata == stored
    assert read_back.metadata.metadata == {
        "Source": "fixture",
        "kind": "original",
    }


def test_s3_private_access_is_expiring_and_not_a_public_url() -> None:
    now = [1000.0]
    storage = make_s3_storage(clock=lambda: now[0])
    storage.put("student-images/work.jpg", b"student original")

    access = storage.create_private_access(
        "student-images/work.jpg",
        expires_in=60,
    )
    assert access.token.startswith("v1.")
    assert "://" not in access.token
    assert storage.read_private(access.token).content == b"student original"

    now[0] = 1060.0
    with pytest.raises(ExpiredPrivateAccessToken):
        storage.read_private(access.token)


def test_s3_private_access_rejects_tampering() -> None:
    storage = make_s3_storage()
    storage.put("private/file.txt", b"content")
    token = storage.create_private_access("private/file.txt").token

    with pytest.raises(InvalidPrivateAccessToken):
        storage.read_private(f"{token}x")


def test_s3_storage_rejects_unsafe_keys_and_collisions() -> None:
    storage = make_s3_storage()
    for key in ("", "../outside.txt", "/absolute", "bad\\key"):
        with pytest.raises(InvalidStorageKey):
            storage.put(key, b"not allowed")

    storage.put("documents/original.txt", b"first version")
    with pytest.raises(ObjectAlreadyExistsError):
        storage.put("documents/original.txt", b"replacement")
    assert storage.get("documents/original.txt").content == b"first version"


def test_s3_storage_reports_missing_objects_and_corruption() -> None:
    client = FakeS3Client()
    storage = make_s3_storage(client)
    with pytest.raises(ObjectNotFoundError):
        storage.get("missing.txt")

    storage.put("documents/file.txt", b"content")
    client.objects["documents/file.txt"]["content"] = b"changed"
    with pytest.raises(StorageIntegrityError):
        storage.get("documents/file.txt")

    storage.delete("documents/file.txt")
    with pytest.raises(ObjectNotFoundError):
        storage.delete("documents/file.txt")


def test_s3_metadata_integrity_hmac_rejects_tampered_metadata() -> None:
    """Altering stored metadata without updating the HMAC must raise StorageIntegrityError."""

    client = FakeS3Client()
    storage = make_s3_storage(client)
    storage.put(
        "books/original.pdf",
        b"original bytes",
        content_type="application/pdf",
        metadata={"author": "lina"},
    )
    # Forge a metadata value directly in the fake store. The bytes are untouched
    # so a bytes-only checksum check would pass; the HMAC must catch this.
    client.objects["books/original.pdf"]["metadata"]["lina-metadata"] = (
        '{"author":"attacker"}'
    )

    with pytest.raises(StorageIntegrityError, match="integrity"):
        storage.head("books/original.pdf")


def test_s3_endpoint_must_be_https() -> None:
    """An http:// endpoint is rejected before client construction."""

    with pytest.raises(ValueError, match="HTTPS"):
        S3ObjectStorage(
            "private-bucket",
            "us-east-1",
            "access",
            "secret",
            endpoint="http://minio.internal:9000",
            signing_secret="test-secret",
        )


def test_s3_endpoint_with_injected_client_bypasses_transport_check() -> None:
    """A test-only injected client skips transport validation — non-HTTPS endpoint is accepted."""

    storage = S3ObjectStorage(
        "private-bucket",
        "us-east-1",
        "access",
        "secret",
        endpoint="http://minio.internal:9000",
        signing_secret="test-secret",
        client=FakeS3Client(),
    )
    storage.put("test.bin", b"payload")
    assert storage.get("test.bin").content == b"payload"