"""Fills a local database with demo data from every sub-app, resetting any earlier seed.

    uv run python -m houseplants.seed      (or `make seed`)

Each sub-app owns its own seed data (houseplants/<sub-app>/seed.py). Users live in Clerk
(or clerk-mock locally), not here: the seed data is owned by the user ids in settings —
by default clerk-mock's `user_demo` and `user_friend` (see mocks/clerk/).
"""

import sys
from datetime import date

from sqlalchemy import make_url
from sqlalchemy.orm import Session

from houseplants.common.db import get_engine
from houseplants.common.settings import get_settings
from houseplants.trips.models import Trip
from houseplants.trips.seed import seed_trips

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "db"}


def is_local_database(database_url: str) -> bool:
    return make_url(database_url).host in LOCAL_HOSTS


def seed(session: Session, today: date) -> list[Trip]:
    settings = get_settings()
    return seed_trips(session, settings.seed_demo_user_id, settings.seed_friend_user_id, today)


def main() -> None:
    database_url = get_settings().database_url
    if not is_local_database(database_url):
        sys.exit(f"Refusing to seed a non-local database ({make_url(database_url).host}).")

    with Session(get_engine()) as session:
        trips = seed(session, date.today())
        print("Seeded trips:")
        for trip in trips:
            print(f"  {trip.id}  {trip.title}  (owner {trip.owner_id}, {len(trip.days)} days)")
        print("Log in as their owners locally via the frontend's login page (clerk-mock).")


if __name__ == "__main__":
    main()
