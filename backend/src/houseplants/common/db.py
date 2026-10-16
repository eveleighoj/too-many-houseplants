from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from houseplants.common.settings import get_settings


def sqlalchemy_url(url: str) -> str:
    """Point a plain postgres:// URL (as Render and docker-compose give it) at psycopg 3."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


@lru_cache
def get_engine() -> Engine:
    return create_engine(sqlalchemy_url(get_settings().database_url), pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request. Tests override this per sub-app."""
    with sessionmaker(get_engine())() as session:
        yield session
