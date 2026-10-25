import uuid
from datetime import date, timedelta

from sqlalchemy import func, select

from api.trips.models import Booking, Place, Stay, Stop, Trip, TripDay
from scripts.api.seed.trips import seed_trips

TODAY = date(2026, 10, 15)
SEEDED = (Place, Trip, TripDay, Stop, Stay, Booking)


def new_user() -> str:
    return f"user_{uuid.uuid4().hex}"


def count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def test_seed_trips_gives_each_owner_trips(session):
    demo, friend = new_user(), new_user()

    trips = seed_trips(session, demo, friend, TODAY)

    owners = [trip.owner_id for trip in trips]
    assert owners.count(friend) >= 1
    assert owners.count(demo) >= 1


def test_seed_trips_dates_every_day_in_the_future(session):
    trips = seed_trips(session, new_user(), new_user(), TODAY)

    assert all(day.date > TODAY for trip in trips for day in trip.days)


def test_seed_trips_replaces_the_previous_seed_keeping_its_ids(session):
    demo, friend = new_user(), new_user()
    first_ids = [trip.id for trip in seed_trips(session, demo, friend, TODAY)]
    counts = [count(session, m) for m in SEEDED]

    second = seed_trips(session, demo, friend, TODAY + timedelta(days=1))

    assert [count(session, m) for m in SEEDED] == counts
    assert [trip.id for trip in second] == first_ids
    assert second[0].days[0].date == TODAY + timedelta(days=31)


def test_seed_trips_replaces_seed_rows_left_by_other_owners(session):
    # e.g. data seeded before the users had fixed ids: same trip ids, different owner.
    seed_trips(session, new_user(), new_user(), TODAY)
    counts = [count(session, m) for m in SEEDED]
    demo, friend = new_user(), new_user()

    trips = seed_trips(session, demo, friend, TODAY)

    assert [count(session, m) for m in SEEDED] == counts
    assert {trip.owner_id for trip in trips} == {demo, friend}


def test_seed_trips_leaves_other_owners_trips_and_places_alone(session, saved_trip):
    places = session.scalar(select(func.count()).where(Place.owner_id == saved_trip.owner_id))

    seed_trips(session, new_user(), new_user(), TODAY)

    assert session.get(Trip, saved_trip.id) is not None
    assert (
        session.scalar(select(func.count()).where(Place.owner_id == saved_trip.owner_id)) == places
    )


def test_seed_trips_only_uses_places_owned_by_the_trips_owner(session):
    trips = seed_trips(session, new_user(), new_user(), TODAY)

    for trip in trips:
        places = [stop.place for day in trip.days for stop in day.stops]
        places += [stay.place for stay in trip.stays] + [b.place for b in trip.bookings]
        assert {place.owner_id for place in places} <= {trip.owner_id}


def test_seed_trips_includes_every_kind_of_booking(session):
    bookings = [
        b for trip in seed_trips(session, new_user(), new_user(), TODAY) for b in trip.bookings
    ]

    assert any(b.stop_id for b in bookings)
    assert any(b.stay_id for b in bookings)
    assert any(not b.stop_id and not b.stay_id for b in bookings)
