"""Shared plumbing for each sub-app's own Alembic chain.

Every chain lives in its own Postgres schema and records its progress in an
`alembic_version` table inside that schema, so chains never see or collide with each other.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, text

from houseplants.common.db import sqlalchemy_url
from houseplants.common.settings import get_settings

# Order matters only for first-time setup convenience; chains don't reference each other.
CHAINS = ["trips"]

PACKAGE_DIR = Path(__file__).resolve().parent.parent


def run_chain_migrations(context, schema: str, target_metadata: MetaData) -> None:
    """Body of an alembic/env.py, parameterised by the chain's schema."""
    url = context.config.get_main_option("sqlalchemy.url") or get_settings().database_url
    engine = create_engine(sqlalchemy_url(url))

    def include_name(name, type_, parent_names):
        if type_ == "schema":
            return name == schema
        return True

    with engine.connect() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=schema,
            include_schemas=True,
            include_name=include_name,
        )
        with context.begin_transaction():
            context.run_migrations()


def alembic_config(chain: str, database_url: str | None = None) -> Config:
    config = Config(str(PACKAGE_DIR / chain / "alembic.ini"))
    if database_url:
        # ConfigParser interpolation treats % specially (e.g. URL-encoded passwords).
        config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def upgrade_all(database_url: str | None = None) -> None:
    for chain in CHAINS:
        command.upgrade(alembic_config(chain, database_url), "head")


if __name__ == "__main__":
    upgrade_all()
