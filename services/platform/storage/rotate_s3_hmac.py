"""Rotate S3 object-metadata HMACs without exposing secret values.

Run with:

    OLD_SESSION_SECRET=... NEW_SESSION_SECRET=... \
    python -m services.platform.storage.rotate_s3_hmac

The secret values should come from the deployment secret manager rather than
command-line arguments, where process listings could expose them.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict

from services.platform.config import Settings

from .s3 import S3ObjectStorage


def _secret_from_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(
            f"Environment variable {name} must contain a non-empty secret."
        )
    return value


def _build_storage(settings: Settings, *, signing_secret: str) -> S3ObjectStorage:
    if settings.storage_provider != "s3":
        raise ValueError(
            "S3 metadata rotation requires STORAGE_PROVIDER=s3; "
            "the local provider does not use S3 object metadata."
        )
    if (
        settings.s3_bucket is None
        or settings.s3_region is None
        or settings.s3_access_key_id is None
        or settings.s3_secret_access_key is None
    ):
        raise ValueError("S3 configuration is incomplete.")
    return S3ObjectStorage(
        bucket=settings.s3_bucket,
        region=settings.s3_region,
        endpoint=settings.s3_endpoint,
        access_key_id=settings.s3_access_key_id.get_secret_value(),
        secret_access_key=settings.s3_secret_access_key.get_secret_value(),
        signing_secret=signing_secret,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Re-sign S3 object metadata with a new SESSION_SECRET without "
            "downloading or replacing object bytes."
        )
    )
    parser.add_argument(
        "--old-secret-env",
        default="OLD_SESSION_SECRET",
        help="Environment variable containing the current signing secret.",
    )
    parser.add_argument(
        "--new-secret-env",
        default="NEW_SESSION_SECRET",
        help="Environment variable containing the replacement signing secret.",
    )
    parser.add_argument(
        "--prefix",
        help="Optional S3 key prefix to rotate instead of the whole bucket.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify the inventory and signatures without writing metadata.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    old_secret = _secret_from_environment(args.old_secret_env)
    new_secret = _secret_from_environment(args.new_secret_env)
    settings = Settings()
    storage = _build_storage(settings, signing_secret=old_secret)
    report = storage.resign_metadata(
        old_signing_secret=old_secret,
        new_signing_secret=new_secret,
        prefix=args.prefix,
        dry_run=args.dry_run,
    )
    print(json.dumps(asdict(report), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())