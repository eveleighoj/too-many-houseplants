"""Acceptance tests drive the whole deployed app (houseplants.main:app) over HTTP, against a
real, migrated database whose contents each test controls. See docs/testing.md."""

import json
import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from sqlalchemy import text
from sqlalchemy.orm import Session

from houseplants.common.db import get_engine
from houseplants.common.migrations import CHAINS
from houseplants.common.settings import get_settings

ACCEPTANCE_DIR = Path(__file__).parent
SCHEMA_BASE_URI = "https://schemas.too-many-houseplants.test/"


def load_schema_registry() -> Registry:
    """Every tests/acceptance/**/schemas/*.json file, addressable by its path relative to
    tests/acceptance — so schemas can $ref each other with relative paths."""
    registry = Registry()
    for path in ACCEPTANCE_DIR.glob("**/schemas/*.json"):
        uri = SCHEMA_BASE_URI + path.relative_to(ACCEPTANCE_DIR).as_posix()
        registry = registry.with_resource(uri, Resource.from_contents(json.loads(path.read_text())))
    return registry.crawl()


@pytest.fixture(scope="session")
def assert_matches_schema() -> Callable[[object, str], None]:
    """assert_matches_schema(body, "trips/schemas/trip-owner.json") — fails listing every
    contract violation, not just the first."""
    registry = load_schema_registry()

    def check(body: object, schema_path: str) -> None:
        uri = SCHEMA_BASE_URI + schema_path
        assert uri in registry, f"no schema at tests/acceptance/{schema_path}"
        validator = Draft202012Validator(
            {"$ref": uri},
            registry=registry,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )
        errors = [
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in validator.iter_errors(body)
        ]
        assert not errors, f"response breaks {schema_path}:\n" + "\n".join(errors)

    return check


@pytest.fixture(scope="session")
def app_database(database_url: str) -> Iterator[None]:
    """Points the app's own settings and engine at the test database."""
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    get_engine.cache_clear()
    yield
    get_engine().dispose()
    if previous is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous
    get_settings.cache_clear()
    get_engine.cache_clear()


@pytest.fixture
def db(app_database) -> Iterator[Session]:
    """A session on the app's database for arranging data. Commit what you add — the app
    reads it over its own connections. Every table is emptied after each test."""
    engine = get_engine()
    with Session(engine) as session:
        yield session

    with engine.begin() as connection:
        tables = connection.execute(
            text(
                "SELECT format('%I.%I', table_schema, table_name) FROM information_schema.tables"
                " WHERE table_schema = ANY(:schemas) AND table_name != 'alembic_version'"
            ),
            {"schemas": CHAINS},
        ).scalars()
        connection.execute(text(f"TRUNCATE {', '.join(tables)} CASCADE"))


@pytest.fixture
def client(db) -> TestClient:
    from houseplants.main import app

    return TestClient(app)
