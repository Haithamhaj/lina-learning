from __future__ import annotations

from io import BytesIO
import multiprocessing
import time

import pytest

from services.platform.storage import (
    ObjectAlreadyExistsError,
    ObjectNotFoundError,
    ReplitObjectStorage,
    StorageIntegrityError,
)


class FakeReplitClient:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def exists(self, key: str) -> bool:
        return key in self.objects

    def upload_from_bytes(self, key: str, content: bytes) -> None:
        self.objects[key] = content

    def download_as_bytes(self, key: str) -> bytes:
        try:
            return self.objects[key]
        except KeyError as exc:
            raise ObjectNotFoundError(key) from exc

    def delete(self, key: str) -> None:
        try:
            del self.objects[key]
        except KeyError as exc:
            raise ObjectNotFoundError(key) from exc


class SharedReplitClient(FakeReplitClient):
    def __init__(self, objects) -> None:
        self.objects = objects


def _contended_put(objects, ready, start, results, content: bytes) -> None:
    storage = ReplitObjectStorage(
        client=SharedReplitClient(objects),
        signing_secret="test-secret",
    )
    ready.append(1)
    start.wait(5)
    try:
        storage.put("student-source/concurrent.pdf", content)
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
            clock=lambda: 1_000.0,
        ),
        client,
    )


def test_replit_storage_preserves_signed_private_metadata_and_bytes() -> None:
    storage, client = make_storage()

    stored = storage.put(
        "student-source/original.pdf",
        BytesIO(b"original"),
        content_type="application/pdf",
        metadata={"student-source-id": "source-1"},
    )

    assert storage.head(stored.key) == stored
    assert storage.get(stored.key).content == b"original"
    assert stored.size == 8
    assert stored.checksum_sha256
    assert any(key.startswith(".lina-replit-metadata/") for key in client.objects)


def test_replit_storage_rejects_replacement_and_removes_both_objects() -> None:
    storage, client = make_storage()
    storage.put("canvas/generated.svg", b"first", content_type="image/svg+xml")

    with pytest.raises(ObjectAlreadyExistsError):
        storage.put("canvas/generated.svg", b"replacement")

    storage.delete("canvas/generated.svg")
    with pytest.raises(ObjectNotFoundError):
        storage.get("canvas/generated.svg")
    assert not client.objects


def test_replit_storage_rejects_tampered_metadata_sidecar() -> None:
    storage, client = make_storage()
    storage.put("books/book.pdf", b"source", metadata={"origin": "parent"})
    metadata_key = storage._metadata_key("books/book.pdf")
    client.objects[metadata_key] = client.objects[metadata_key].replace(
        b'"parent"', b'"forged"'
    )

    with pytest.raises(StorageIntegrityError):
        storage.head("books/book.pdf")


def test_replit_storage_allows_only_one_api_or_worker_writer_on_the_reserved_vm() -> None:
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
        while len(ready) < len(processes) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(ready) == len(processes)
        start.set()
        for process in processes:
            process.join(timeout=10)
            assert process.exitcode == 0
        assert sorted(results.get(timeout=2) for _ in processes) == ["collision", "winner"]
