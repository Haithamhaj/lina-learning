from io import BytesIO
from pathlib import Path

import pytest

from services.platform.config import Settings
from services.platform.storage import (
    ExpiredPrivateAccessToken,
    InvalidPrivateAccessToken,
    InvalidStorageKey,
    LocalObjectStorage,
    ObjectAlreadyExistsError,
    ObjectNotFoundError,
    StorageProviderUnavailable,
    StorageIntegrityError,
    create_object_storage,
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

    for key in ("", ".", "../outside.txt", "nested/../../outside", "/absolute", "bad\\key"):
        with pytest.raises(InvalidStorageKey):
            storage.put(key, b"not allowed")

    assert not (tmp_path / "outside.txt").exists()


def test_delete_removes_object_and_metadata(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path / "private", signing_secret="test-secret")
    storage.put("documents/file.txt", b"content")

    storage.delete("documents/file.txt")

    with pytest.raises(ObjectNotFoundError):
        storage.get("documents/file.txt")
    assert not list((tmp_path / "private").rglob("*"))


def test_put_does_not_replace_an_existing_original(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path / "private", signing_secret="test-secret")
    storage.put("documents/original.txt", b"first version")

    with pytest.raises(ObjectAlreadyExistsError):
        storage.put("documents/original.txt", b"replacement")

    assert storage.get("documents/original.txt").content == b"first version"


def test_corrupt_bytes_fail_integrity_check(tmp_path: Path) -> None:
    storage = LocalObjectStorage(tmp_path / "private", signing_secret="test-secret")
    storage.put("documents/file.txt", b"content")
    (tmp_path / "private" / "documents" / "file.txt").write_bytes(b"changed")

    with pytest.raises(StorageIntegrityError):
        storage.get("documents/file.txt")


def test_storage_factory_defaults_to_local(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, storage_dir=tmp_path / "configured")

    storage = create_object_storage(settings)

    assert isinstance(storage, LocalObjectStorage)
    storage.put("fixture.bin", b"fixture")


def test_storage_factory_rejects_deferred_s3_provider(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        storage_provider="s3",
        storage_dir=tmp_path,
        s3_bucket="bucket",
        s3_region="region",
        s3_access_key_id="access",
        s3_secret_access_key="secret",
    )

    with pytest.raises(StorageProviderUnavailable, match="reserved"):
        create_object_storage(settings)