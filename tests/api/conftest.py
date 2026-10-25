"""Fixtures shared by every test type. See docs/testing.md.

Database fixtures are lazy: unit tests never request them, so they never start a container.
"""

import json
import os
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import create_engine, make_url, text

# --- A test token issuer -------------------------------------------------------------------
# Stands in for Clerk: an RSA key pair made fresh for each run, whose public half is served as a
# JWKS over HTTP on a random local port (the app fetches it exactly as it fetches Clerk's).
# Tokens signed with the private half pass the app's real verification.
TEST_ISSUER = "https://issuer.test"
TEST_AUTHORIZED_PARTY = "http://frontend.test"
TEST_KEY_ID = "test-key"
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(_private_key.public_key()))
_jwks = json.dumps({"keys": [{**_jwk, "kid": TEST_KEY_ID, "use": "sig", "alg": "RS256"}]})


class _JwksHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (http.server's naming)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(_jwks.encode())

    def log_message(self, *args):  # keep test output quiet
        pass


_jwks_server = ThreadingHTTPServer(("127.0.0.1", 0), _JwksHandler)
threading.Thread(target=_jwks_server.serve_forever, daemon=True).start()

# Fixed, so tests never depend on whatever is in a developer's .env (environment variables
# take precedence over .env in Settings). Set before anything reads settings.
os.environ["AUTH_ISSUER"] = TEST_ISSUER
os.environ["AUTH_JWKS_URL"] = f"http://127.0.0.1:{_jwks_server.server_port}/jwks.json"
os.environ["AUTH_AUTHORIZED_PARTIES"] = TEST_AUTHORIZED_PARTY
os.environ["ALLOWED_ORIGINS"] = "http://frontend.test"
os.environ["UKHO_API_KEY"] = "test-ukho-key"

from api.common.migrations import upgrade_all  # noqa: E402
from api.common.security import get_token_verifier  # noqa: E402
from api.common.settings import get_settings  # noqa: E402

get_settings.cache_clear()
get_token_verifier.cache_clear()


def sign_token(claims: dict, key=_private_key, kid: str = TEST_KEY_ID) -> str:
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


@pytest.fixture
def make_token() -> Callable[..., str]:
    """make_token(sub, **claims) -> a token the app accepts, like one Clerk would issue.
    Override or remove (claim=None) any claim to build an invalid one."""

    def build(sub: str = "user_test", **overrides) -> str:
        now = int(time.time())
        claims = {
            "sub": sub,
            "iss": TEST_ISSUER,
            "azp": TEST_AUTHORIZED_PARTY,
            "iat": now,
            "nbf": now,
            "exp": now + 60,
        }
        claims.update(overrides)
        return sign_token({k: v for k, v in claims.items() if v is not None})

    return build


@pytest.fixture
def auth_header(make_token) -> Callable[[str], dict[str, str]]:
    """Builds an Authorization header carrying a valid token for the given user id."""

    def build(user_id: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {make_token(str(user_id))}"}

    return build


@pytest.fixture
def user_id() -> str:
    """A fresh Clerk-style user id."""
    return f"user_{uuid.uuid4().hex}"


@pytest.fixture(scope="session")
def postgres_server_url() -> Iterator[str]:
    """A throwaway Postgres container for the whole test run."""
    from testcontainers.community.postgres import PostgresContainer

    with PostgresContainer("postgres:16", driver="psycopg") as container:
        yield container.get_connection_url()


@pytest.fixture(scope="session")
def create_database(postgres_server_url: str) -> Callable:
    """Context manager factory: an empty, uniquely named database, dropped afterwards."""
    admin = create_engine(postgres_server_url, isolation_level="AUTOCOMMIT")

    @contextmanager
    def create() -> Iterator[str]:
        name = f"test_{uuid.uuid4().hex[:12]}"
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
        try:
            yield (
                make_url(postgres_server_url)
                .set(database=name)
                .render_as_string(hide_password=False)
            )
        finally:
            with admin.connect() as connection:
                connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))

    yield create
    admin.dispose()


@pytest.fixture(scope="session")
def database_url(create_database) -> Iterator[str]:
    """One database for the run, with every Alembic chain applied."""
    with create_database() as url:
        upgrade_all(url)
        yield url
