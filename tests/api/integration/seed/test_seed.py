from datetime import date

from scripts.api.seed import SeedSettings, seed


def test_seed_gives_the_trips_to_the_configured_seed_users(session):
    settings = SeedSettings(seed_demo_user_id="user_a", seed_friend_user_id="user_b")

    trips = seed(session, date(2026, 10, 15), settings)

    assert trips
    assert {trip.owner_id for trip in trips} == {"user_a", "user_b"}


def test_seed_settings_default_to_the_clerk_mock_dev_users():
    settings = SeedSettings(_env_file=None)

    assert (settings.seed_demo_user_id, settings.seed_friend_user_id) == (
        "user_demo",
        "user_friend",
    )
