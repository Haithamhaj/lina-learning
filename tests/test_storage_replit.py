from datetime import UTC
from io import BytesIO
import multiprocessing
import time

import pytest

from services.platform.config import Settings
from services.platform.storage import (
    ObjectAlreadyExistsError,
    ObjectNotFoundError,
    ReplitObjectStorage,
    StorageIntegrityError,
    StorageProviderUnavailable,
    create_object_storage,
)


class FakeReplitClient:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def exists(self, name: str) -> bool:
        return name in self.objects

    def upload_from_bytes(self, name: str, content: bytes) -> None:
        self.objects[name] = content

    def download_as_bytes(self, name: str) -> bytes:
        try:
            return self.objects[name]
        except KeyError:
            raise ObjectNotFoundError(name) from None

    def delete(self, name: str) -> None:
        try:
            del self.objects[name]
        except KeyError:
            raise ObjectNotFoundError(name) from None


class SharedReplitClient:
    """Manager-backed fake so two OS processes share one bucket."""

    def __init__(self, objects) -> None:
        self.objects = objects

    def exists(self, name: str) -> bool:
        return name in self.objects

    def upload_from_bytes(self, name: str, content: bytes) -> None:
        self.objects[name] = content

    def download_as_bytes(self, name: str) -> bytes:
        try:
            return self.objects[name]
        except KeyError:
            raise ObjectNotFoundError(name) from None

    def delete(self, name: str) -> None:
        try:
            del self.objects[name]
        except KeyError:
            raise ObjectNotFoundError(name) from None


def _contended_put(objects, ready, start, results, content: bytes) -> None:
    storage = ReplitObjectStorage(
        client=SharedReplitClient(objects),
        signing_secret="test-secret",
        lock_timeout=2.0,
    )
    ready.append(1)
    start.wait(5)
    try:
        storage.put("processes/concurrent.bin", content)
    except ObjectAlreadyExistsError:
        results.put("collision")
    else:
        results.put("winner")


def make_storage() -> tuple[ReplitObjectStorage, FakeReplitClient]:
    client = FakeReplitClient()
    return (
        ReplitObjectStorage(
            client=client,
            signing_secret="test-secret",
            clock=lambda: 1000.0,
        ),
        client,
    )


def test_replit_storage_preserves_bytes_metadata_and_checksum() -> None:
    storage, client = make_storage()

    stored = storage.put(
        "books/original.pdf",
        BytesIO(b"original"),
        content_type="application/pdf",
        metadata={"source": "student"},
    )

    assert storage.head(stored.key) == stored
    assert storage.get(stored.key).content == b"original"
    assert stored.size == 8
    assert len(stored.checksum_sha256) == 64
    assert stored.stored_at is not None and stored.stored_at.tzinfo is UTC
    assert any(name.startswith(".lina-replit-metadata/") for name in client.objects)


def test_replit_storage_is_immutable_and_delete_removes_sidecar() -> None:
    storage, client = make_storage()
    storage.put("documents/file.txt", b"first")

    with pytest.raises(ObjectAlreadyExistsError):
        storage.put("documents/file.txt", b"replacement")

    storage.delete("documents/file.txt")
    with pytest.raises(ObjectNotFoundError):
        storage.get("documents/file.txt")
    assert not any(name.startswith(".lina-replit-metadata/") for name in client.objects)


def test_replit_storage_detects_changed_bytes() -> None:
    storage, client = make_storage()
    storage.put("documents/file.txt", b"content")
    client.objects["documents/file.txt"] = b"changed"

    with pytest.raises(StorageIntegrityError):
        storage.get("documents/file.txt")


def test_failed_upload_before_bytes_resumes_only_identical_put() -> None:
    class FailingClient(FakeReplitClient):
        fail_once = True

        def upload_from_bytes(self, name: str, content: bytes) -> None:
            if name == "documents/failed.txt" and self.fail_once:
                self.fail_once = False
                raise RuntimeError("simulated upload failure")
            super().upload_from_bytes(name, content)

    client = FailingClient()
    storage = ReplitObjectStorage(client=client, signing_secret="test-secret")

    with pytest.raises(StorageProviderUnavailable, match="upload failed"):
        storage.put(
            "documents/failed.txt",
            b"content",
            content_type="text/plain",
            metadata={"source": "test"},
        )
    stored = storage.put(
        "documents/failed.txt",
        b"content",
        content_type="text/plain",
        metadata={"source": "test"},
    )
    assert storage.get(stored.key).content == b"content"
    with pytest.raises(ObjectAlreadyExistsError):
        storage.put("documents/failed.txt", b"replacement")


def test_failed_upload_after_bytes_resumes_only_identical_put() -> None:
    class FailingMetadataClient(FakeReplitClient):
        fail_complete_once = True
        metadata_key: str

        def upload_from_bytes(self, name: str, content: bytes) -> None:
            if (
                name == self.metadata_key
                and name in self.objects
                and self.fail_complete_once
            ):
                self.fail_complete_once = False
                raise RuntimeError("simulated metadata upload failure")
            super().upload_from_bytes(name, content)

    client = FailingMetadataClient()
    storage = ReplitObjectStorage(client=client, signing_secret="test-secret")
    client.metadata_key = storage._metadata_key("documents/failed.txt")

    with pytest.raises(StorageProviderUnavailable, match="upload failed"):
        storage.put(
            "documents/failed.txt",
            b"content",
            content_type="text/plain",
            metadata={"source": "test"},
        )
    assert client.objects["documents/failed.txt"] == b"content"

    stored = storage.put(
        "documents/failed.txt",
        b"content",
        content_type="text/plain",
        metadata={"source": "test"},
    )
    assert storage.get(stored.key).content == b"content"
    with pytest.raises(ObjectAlreadyExistsError):
        storage.put(
            "documents/failed.txt",
            b"replacement",
            content_type="text/plain",
            metadata={"source": "test"},
        )


def test_replit_process_contention_has_one_winner_and_one_collision() -> None:
    context = multiprocessing.get_context("fork")
    with context.Manager() as manager:
        objects = manager.dict()
        ready = manager.list()
        start = context.Event()
        results = context.Queue()
        processes = [
            context.Process(
                target=_contended_put,
                args=(objects, ready, start, results, content),
            )
            for content in (b"first", b"second")
        ]
        for process in processes:
            process.start()
        deadline = time.monotonic() + 5
        while len(ready) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(ready) == 2
        start.set()
        for process in processes:
            process.join(timeout=10)
            assert process.exitcode == 0

        assert sorted(results.get(timeout=2) for _ in processes) == [
            "collision",
            "winner",
        ]
        assert objects["processes/concurrent.bin"] in {b"first", b"second"}


def test_replit_private_access_is_server_capability() -> None:
    now = [1000.0]
    client = FakeReplitClient()
    storage = ReplitObjectStorage(
        client=client,
        signing_secret="test-secret",
        clock=lambda: now[0],
    )
    storage.put("private/file.txt", b"content")
    access = storage.create_private_access("private/file.txt", expires_in=10)

    assert access.url is None
    assert "://" not in access.token
    assert storage.read_private(access.token).content == b"content"


def test_replit_factory_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = object()
    monkeypatch.setattr(
        "services.platform.storage.factory.ReplitObjectStorage",
        lambda **kwargs: (expected, kwargs),
    )

    result = create_object_storage(
        Settings(
            _env_file=None,
            storage_provider="replit",
            replit_storage_bucket_id="bucket-id",
            session_secret="secret",
        )
    )

    assert result == (
        expected,
        {"bucket_id": "bucket-id", "signing_secret": "secret"},
    )