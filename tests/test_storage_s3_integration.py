"""Opt-in end-to-end checks against a real S3-compatible bucket.

These tests are intentionally separate from the provider contract tests so the
normal suite never needs network access or cloud credentials. Set the
integration environment variables described in docs/OBJECT_STORAGE.md to run
them against a non-production bucket.
"""

from __future__ import annotations

from collections.abc import Iterator
from hashlib import sha256
from io import BytesIO
import os
from uuid import uuid4

import pytest

from services.platform.storage import (
    ObjectAlreadyExistsError,
    ObjectNotFoundError,
    S3ObjectStorage,
    StorageIntegrityError,
)


_REQUIRED_ENVIRONMENT = (
    "S3_BUCKET",
    "S3_REGION",
    "S3_ACCESS_KEY_ID",
    "S3_SECRET_ACCESS_KEY",
    "SESSION_SECRET",
)
_RUN_INTEGRATION_TESTS = os.environ.get("RUN_S3_INTEGRATION_TESTS") == "1"
_MISSING_ENVIRONMENT = tuple(
    name for name in _REQUIRED_ENVIRONMENT if not os.environ.get(name)
)

pytestmark = [
    pytest.mark.s3_integration,
    pytest.mark.skipif(
        not _RUN_INTEGRATION_TESTS or _MISSING_ENVIRONMENT,
        reason=(
            (
                "Set RUN_S3_INTEGRATION_TESTS=1 to acknowledge cloud writes; "
                if not _RUN_INTEGRATION_TESTS
                else "S3 integration settings are not configured; missing "
                + ", ".join(_MISSING_ENVIRONMENT)
            )
        ),
    ),
]


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required for S3 integration tests")
    return value


@pytest.fixture(scope="module")
def real_s3_storage() -> S3ObjectStorage:
    """Build the production client path, including endpoint validation."""

    return S3ObjectStorage(
        bucket=_required_environment("S3_BUCKET"),
        region=_required_environment("S3_REGION"),
        access_key_id=_required_environment("S3_ACCESS_KEY_ID"),
        secret_access_key=_required_environment("S3_SECRET_ACCESS_KEY"),
        endpoint=os.environ.get("S3_ENDPOINT") or None,
        signing_secret=_required_environment("SESSION_SECRET"),
    )


@pytest.fixture
def integration_key(
    real_s3_storage: S3ObjectStorage,
    request: pytest.FixtureRequest,
) -> Iterator[str]:
    """Use an isolated key and remove it even when an assertion fails."""

    key = f"tests/s3-integration/{uuid4().hex}/{request.node.name}.bin"
    try:
        yield key
    finally:
        try:
            real_s3_storage.delete(key)
        except ObjectNotFoundError:
            pass


def test_real_s3_round_trip_and_private_access(
    real_s3_storage: S3ObjectStorage,
    integration_key: str,
) -> None:
    """A binary stream survives put, head, get, and private capability reads."""

    payload = bytes(range(256)) * 31 + b"\x00\xff Lina original bytes \x00"
    stored = real_s3_storage.put(
        integration_key,
        BytesIO(payload),
        content_type="application/octet-stream",
        metadata={"source": "s3-integration", "kind": "original"},
    )

    assert stored.key == integration_key
    assert stored.size == len(payload)
    assert stored.checksum_sha256 == sha256(payload).hexdigest()
    assert real_s3_storage.head(integration_key) == stored

    downloaded = real_s3_storage.get(integration_key)
    assert downloaded.content == payload
    assert downloaded.metadata == stored

    private_access = real_s3_storage.create_private_access(
        integration_key,
        expires_in=60,
    )
    assert private_access.url is None
    assert real_s3_storage.read_private(private_access.token).content == payload


def test_real_s3_collision_protection_preserves_original(
    real_s3_storage: S3ObjectStorage,
    integration_key: str,
) -> None:
    """The real provider rejects a second write using S3's conditional put."""

    original = b"first immutable original"
    real_s3_storage.put(integration_key, original)

    with pytest.raises(ObjectAlreadyExistsError):
        real_s3_storage.put(integration_key, b"replacement bytes")

    assert real_s3_storage.get(integration_key).content == original


def test_real_s3_hmac_rejects_out_of_band_metadata_change(
    real_s3_storage: S3ObjectStorage,
    integration_key: str,
) -> None:
    """A bucket-level metadata rewrite cannot bypass application integrity checks."""

    payload = b"original bytes remain unchanged"
    real_s3_storage.put(
        integration_key,
        payload,
        metadata={"owner": "student"},
    )
    client = real_s3_storage._client
    head_response = client.head_object(
        Bucket=real_s3_storage.bucket,
        Key=integration_key,
    )
    tampered_metadata = dict(head_response["Metadata"])
    tampered_metadata["lina-metadata"] = '{"owner":"attacker"}'

    try:
        # Bypass the application and imitate an out-of-band bucket writer.
        # PutObject is used instead of CopyObject so the staging policy only
        # needs the same PutObject permission as normal application uploads.
        client.put_object(
            Bucket=real_s3_storage.bucket,
            Key=integration_key,
            Body=BytesIO(payload),
            ContentType=head_response["ContentType"],
            Metadata=tampered_metadata,
        )

        with pytest.raises(StorageIntegrityError, match="integrity"):
            real_s3_storage.head(integration_key)
    finally:
        # The provider correctly refuses to delete an object with forged
        # metadata, so this test's teardown must use the raw client.
        client.delete_object(
            Bucket=real_s3_storage.bucket,
            Key=integration_key,
        )


def test_real_s3_delete_removes_object(
    real_s3_storage: S3ObjectStorage,
    integration_key: str,
) -> None:
    real_s3_storage.put(integration_key, b"delete me")

    real_s3_storage.delete(integration_key)

    with pytest.raises(ObjectNotFoundError):
        real_s3_storage.get(integration_key)