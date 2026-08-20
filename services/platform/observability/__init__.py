"""Provider-neutral operational signals."""

from .metrics import (
    STORAGE_FAILURES_TOTAL,
    StorageCounterRegistry,
    StorageCounterSink,
    storage_key_prefix,
    storage_counters,
)

__all__ = [
    "STORAGE_FAILURES_TOTAL",
    "StorageCounterRegistry",
    "StorageCounterSink",
    "storage_counters",
    "storage_key_prefix",
]