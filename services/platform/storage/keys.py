"""Shared validation for provider-neutral object keys."""

from pathlib import PurePosixPath

from .models import InvalidStorageKey


def validate_storage_key(key: str) -> str:
    """Return a canonical relative key or reject path traversal."""

    if not isinstance(key, str) or not key:
        raise InvalidStorageKey("Storage keys must be non-empty strings.")
    if "\x00" in key or "\\" in key or key.startswith("/"):
        raise InvalidStorageKey("Storage keys must use safe relative POSIX paths.")

    path = PurePosixPath(key)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise InvalidStorageKey(
            "Storage keys cannot be absolute, normalized, or traverse directories."
        )
    if not path.parts or path.parts[0] == ".locks":
        raise InvalidStorageKey("The .locks namespace is reserved by storage.")
    canonical = "/".join(path.parts)
    if canonical != key:
        raise InvalidStorageKey("Storage keys must be canonical POSIX paths.")
    return canonical