"""Small, dependency-free structured counters for operational signals."""

from __future__ import annotations

import json
import logging
from collections import Counter
from threading import Lock
from typing import Protocol

STORAGE_FAILURES_TOTAL = "lina_storage_operation_failures_total"
_logger = logging.getLogger(__name__)


class StorageCounterSink(Protocol):
    """Sink for storage counters, suitable for adapters to metric backends."""

    def increment(
        self,
        metric: str,
        *,
        provider: str,
        operation: str,
        key_prefix: str,
        amount: int = 1,
    ) -> None:
        """Increment a labeled counter without receiving the full object key."""


def storage_key_prefix(key: str) -> str:
    """Return a bounded, non-secret prefix suitable for metric labels."""

    if key.startswith(".lina-multipart/"):
        return ".lina-multipart/"
    if "/" not in key:
        return "<root>/"
    first_segment = key.split("/", 1)[0]
    return f"{first_segment}/" if first_segment else "<root>/"


class StorageCounterRegistry:
    """In-process counters that also emit structured log records.

    The default logger output is intentionally the operational integration
    point: Replit or a log pipeline can turn the JSON event into a metric. The
    snapshot method makes the same signal directly consumable by a metrics
    adapter or deterministic tests.
    """

    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self._counts: Counter[tuple[str, str, str, str]] = Counter()
        self._lock = Lock()
        self._logger = logger or _logger

    def increment(
        self,
        metric: str,
        *,
        provider: str,
        operation: str,
        key_prefix: str,
        amount: int = 1,
    ) -> None:
        if not metric or not provider or not operation or not key_prefix:
            raise ValueError("Counter names and labels must be non-empty.")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
            raise ValueError("Counter increments must be positive integers.")

        labels = (metric, provider, operation, key_prefix)
        with self._lock:
            self._counts[labels] += amount
            total = self._counts[labels]

        event = {
            "count": total,
            "increment": amount,
            "key_prefix": key_prefix,
            "metric": metric,
            "operation": operation,
            "provider": provider,
        }
        self._logger.warning(
            "storage_counter %s",
            json.dumps(event, separators=(",", ":"), sort_keys=True),
        )

    def snapshot(self) -> dict[tuple[str, str, str, str], int]:
        """Return a copy of counters keyed by metric and safe labels."""

        with self._lock:
            return dict(self._counts)


storage_counters = StorageCounterRegistry()