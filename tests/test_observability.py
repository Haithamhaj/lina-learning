import logging

from services.platform.observability import (
    STORAGE_FAILURES_TOTAL,
    StorageCounterRegistry,
    storage_key_prefix,
)


def test_storage_key_prefix_never_contains_root_object_name() -> None:
    assert storage_key_prefix("private.pdf") == "<root>/"
    assert storage_key_prefix(".lina-multipart/random-value") == ".lina-multipart/"
    assert storage_key_prefix("student-files/private.pdf") == "student-files/"


def test_storage_counter_registry_accumulates_safe_labeled_counts(
    caplog,
) -> None:
    caplog.set_level(logging.WARNING)
    counters = StorageCounterRegistry()

    counters.increment(
        STORAGE_FAILURES_TOTAL,
        provider="s3",
        operation="staging_cleanup",
        key_prefix=".lina-multipart/",
    )
    counters.increment(
        STORAGE_FAILURES_TOTAL,
        provider="s3",
        operation="staging_cleanup",
        key_prefix=".lina-multipart/",
        amount=2,
    )

    assert counters.snapshot() == {
        (
            STORAGE_FAILURES_TOTAL,
            "s3",
            "staging_cleanup",
            ".lina-multipart/",
        ): 3
    }
    assert caplog.records[-1].message.endswith(
        '"operation":"staging_cleanup","provider":"s3"}'
    )