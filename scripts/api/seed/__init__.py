"""Local demo data for the api service. Run from the repo root with `make seed`
(= `uv run python -m scripts.api.seed`). Never shipped in an image.

Each sub-app's seed data has its own module here (trips.py), and every row gets a fixed,
readable id (ids.py). Users live in Clerk (clerk-mock locally), not in our database: the seed
data is owned by the user ids below — by default clerk-mock's dev users.
"""

from datetime import date

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import make_url
from sqlalchemy.orm import Session

from api.trips.models import Trip
from scripts.api.seed.trips import seed_trips

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "db"}


class SeedSettings(BaseSettings):
    """Who owns the seed data. Set SEED_DEMO_USER_ID to your own Clerk user id to own the
    demo trips when using a real Clerk instance."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    seed_demo_user_id: str = "user_demo"
    seed_friend_user_id: str = "user_friend"


def is_local_database(database_url: str) -> bool:
    return make_url(database_url).host in LOCAL_HOSTS


def seed(session: Session, today: date, settings: SeedSettings | None = None) -> list[Trip]:
    settings = settings or SeedSettings()
    return seed_trips(session, settings.seed_demo_user_id, settings.seed_friend_user_id, today)
