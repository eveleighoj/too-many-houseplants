from datetime import date

from houseplants.common.settings import get_settings
from houseplants.seed import seed


def test_seed_gives_the_trips_to_the_configured_seed_users(session):
    settings = get_settings()

    trips = seed(session, date(2026, 10, 15))

    assert trips
    assert {trip.owner_id for trip in trips} == {
        settings.seed_demo_user_id,
        settings.seed_friend_user_id,
    }
