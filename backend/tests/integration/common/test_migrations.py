import pytest
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from houseplants.common.migrations import CHAINS, alembic_config, upgrade_all


@pytest.fixture
def fresh_database_url(create_database):
    with create_database() as url:
        yield url


def current_revision(url: str, chain: str) -> str | None:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection, opts={"version_table_schema": chain})
            return context.get_current_revision()
    finally:
        engine.dispose()


def head_revision(chain: str) -> str:
    return ScriptDirectory.from_config(alembic_config(chain)).get_current_head()


def tables_in(url: str, schema: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names(schema=schema))
    finally:
        engine.dispose()


def test_upgrade_all_applies_every_chain_to_head(fresh_database_url):
    upgrade_all(fresh_database_url)

    for chain in CHAINS:
        assert current_revision(fresh_database_url, chain) == head_revision(chain)


def test_upgrade_all_is_idempotent(fresh_database_url):
    upgrade_all(fresh_database_url)
    upgrade_all(fresh_database_url)

    for chain in CHAINS:
        assert current_revision(fresh_database_url, chain) == head_revision(chain)


@pytest.mark.parametrize("chain", CHAINS)
def test_run_chain_migrations_keeps_version_table_in_the_chains_schema(fresh_database_url, chain):
    command.upgrade(alembic_config(chain, fresh_database_url), "head")

    assert "alembic_version" in tables_in(fresh_database_url, chain)
    assert "alembic_version" not in tables_in(fresh_database_url, "public")


@pytest.mark.parametrize("chain", CHAINS)
def test_run_chain_migrations_matches_the_models(fresh_database_url, chain):
    config = alembic_config(chain, fresh_database_url)
    command.upgrade(config, "head")

    # Raises if the models have changes no migration covers yet.
    command.check(config)


@pytest.mark.parametrize("chain", CHAINS)
def test_run_chain_migrations_downgrades_to_base_and_back(fresh_database_url, chain):
    config = alembic_config(chain, fresh_database_url)
    command.upgrade(config, "head")

    command.downgrade(config, "base")
    assert tables_in(fresh_database_url, chain) == {"alembic_version"}

    command.upgrade(config, "head")
    assert current_revision(fresh_database_url, chain) == head_revision(chain)
