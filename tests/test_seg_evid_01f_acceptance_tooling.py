"""Safety contracts for the SEG-EVID-01F real-model acceptance harness."""

from __future__ import annotations

import pytest

from scripts.run_seg_evid_01f_acceptance import AcceptanceConfigurationError, validate_configuration


def test_f_acceptance_requires_a_unique_isolated_openai_luna_target() -> None:
    source = "postgresql+psycopg://source:secret@127.0.0.1:55433/lina_learning_demo"
    target = "postgresql+psycopg://target:secret@127.0.0.1:55433/lina_acceptance_20260830_f"

    configuration = validate_configuration(
        source_database_url=source,
        target_database_url=target,
        provider="openai",
        model="gpt-5.6-luna",
    )

    assert configuration.target.database == "lina_acceptance_20260830_f"
    assert "secret" not in repr(configuration)
    with pytest.raises(AcceptanceConfigurationError):
        validate_configuration(
            source_database_url=source,
            target_database_url=source,
            provider="openai",
            model="gpt-5.6-luna",
        )
    with pytest.raises(AcceptanceConfigurationError):
        validate_configuration(
            source_database_url=source,
            target_database_url=target,
            provider="mock",
            model="mock",
        )
