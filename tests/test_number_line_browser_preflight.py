"""Pure contract checks for the guarded number-line acceptance preflight."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from collections import UserDict

import pytest


def setup_module():
    path = Path(__file__).parents[1] / 'scripts' / 'number_line_browser_setup.py'
    spec = spec_from_file_location('number_line_browser_setup', path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_rejects_a_non_daily_container_before_browser_writes():
    setup = setup_module()
    with pytest.raises(RuntimeError, match='expected Daily-use database'):
        setup.preflight_database_target(
            {'Name': 'lina-local-demo-postgres', 'Config': {'Env': ['POSTGRES_DB=lina_learning_demo']}},
            database_name='lina_learning_demo',
            student_row={'id': str(setup.TEST_STUDENT), 'user_id': 'local-user'},
            schema_version='head',
            expected_schema_version='head',
        )


def test_preflight_returns_sanitized_identity_only_for_the_expected_target():
    setup = setup_module()
    result = setup.preflight_database_target(
        {'Name': '/lina-learning-daily-use-postgres', 'Config': {'Env': ['POSTGRES_DB=lina_daily_use']}},
        database_name='lina_daily_use',
        student_row={'id': str(setup.TEST_STUDENT), 'user_id': 'local-user'},
        schema_version='head',
        expected_schema_version='head',
    )
    assert result == {
        'container': 'lina-learning-daily-use-postgres',
        'database_name': 'lina_daily_use',
        'authorized_test_student': str(setup.TEST_STUDENT),
        'local_user_id': 'local-user',
        'schema_version': 'head',
    }


def test_preflight_reads_the_repository_migration_head():
    assert setup_module().expected_schema_version() == 'c7d8e9f0a1b2'


def test_preflight_accepts_the_database_row_mapping_returned_by_sqlalchemy():
    setup = setup_module()
    result = setup.preflight_database_target(
        {'Name': '/lina-learning-daily-use-postgres', 'Config': {'Env': ['POSTGRES_DB=lina_daily_use']}},
        database_name='lina_daily_use',
        student_row=UserDict(id=str(setup.TEST_STUDENT), user_id='local-user'),
        schema_version='head',
        expected_schema_version='head',
    )
    assert result['authorized_test_student'] == str(setup.TEST_STUDENT)


def test_every_browser_setup_mode_that_can_write_requires_preflight():
    setup = setup_module()
    assert setup.requires_preflight('api')
    assert setup.requires_preflight('prepare')
    assert not setup.requires_preflight('readback')


def test_prepare_continues_after_its_successful_preflight():
    setup = setup_module()
    assert not setup.exits_after_preflight('prepare')
    assert setup.exits_after_preflight('preflight')
