"""Fills a local database with the demo data, resetting any earlier seed.

make seed        (= uv run python -m scripts.api.seed, from the repo root)
"""

import sys
from datetime import date

from sqlalchemy import make_url
from sqlalchemy.orm import Session

from api.common.db import get_engine
from api.common.settings import get_settings
from scripts.api.seed import is_local_database, seed


def main() -> None:
    database_url = get_settings().database_url
    if not is_local_database(database_url):
        sys.exit(f"Refusing to seed a non-local database ({make_url(database_url).host}).")

    with Session(get_engine()) as session:
        trips = seed(session, date.today())
        print("Seeded trips:")
        for trip in trips:
            print(f"  {trip.id}  {trip.title}  (owner {trip.owner_id}, {len(trip.days)} days)")
        print("Sign in as any user on the frontend's login page to see them (docs/trips.md).")


if __name__ == "__main__":
    main()
