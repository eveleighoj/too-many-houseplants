import uuid

import pytest
from fastapi import HTTPException

from api.trips.api import CreateTrip, create_trip, get_trip, list_trips
from api.trips.models import Trip


def test_create_trip_saves_trip_owned_by_the_caller(session, owner_id):
    view = create_trip(CreateTrip(title="Wales"), str(owner_id), session)

    saved = session.get(Trip, uuid.UUID(view.id))
    assert saved.owner_id == owner_id
    assert saved.title == "Wales"


def test_create_trip_returns_the_trip_with_nothing_planned(session, owner_id):
    view = create_trip(CreateTrip(title="Wales"), str(owner_id), session)

    assert view.title == "Wales"
    assert (view.days, view.stays, view.bookings) == ([], [], [])


def test_list_trips_returns_everyones_trips(session, saved_trip):
    create_trip(CreateTrip(title="Someone else's"), "user_someone_else", session)

    result = list_trips("user_friend", session)

    assert sorted(trip.title for trip in result.trips) == ["Scotland", "Someone else's"]


def test_list_trips_returns_newest_first(session, owner_id):
    first = create_trip(CreateTrip(title="First"), str(owner_id), session)
    second = create_trip(CreateTrip(title="Second"), str(owner_id), session)
    # Both inserts share one transaction (and so one now()) in this test; force an order.
    session.get(Trip, uuid.UUID(first.id)).created_at = session.get(
        Trip, uuid.UUID(second.id)
    ).created_at.replace(year=2000)
    session.commit()

    result = list_trips(str(owner_id), session)

    assert [trip.title for trip in result.trips] == ["Second", "First"]


def test_list_trips_returns_full_details(session, saved_trip):
    result = list_trips("user_friend", session)

    assert result.trips[0].days[0].date is not None
    assert result.trips[0].stays


def test_get_trip_returns_days_and_stops_in_order(session, saved_trip):
    view = get_trip(saved_trip.id, "user_friend", session)

    assert [day.day_number for day in view.days] == [1, 2]
    assert [stop.place.name for stop in view.days[0].stops] == ["Spean Bridge", "Fort William"]


@pytest.mark.parametrize("caller", ["owner", "user_friend"])
def test_get_trip_returns_full_detail_to_any_signed_in_user(session, saved_trip, caller):
    user_id = str(saved_trip.owner_id) if caller == "owner" else caller

    view = get_trip(saved_trip.id, user_id, session)

    assert view.days[0].date is not None
    assert [(stay.place.name, stay.nights) for stay in view.stays] == [("Spean Bridge Hotel", 2)]
    bookings = {booking.reference: booking for booking in view.bookings}
    assert bookings["ABC123"].stop_id == view.days[0].stops[0].id
    assert bookings["HOTEL-1"].stay_id == view.stays[0].id


def test_get_trip_raises_404_for_unknown_trip(session):
    with pytest.raises(HTTPException) as error:
        get_trip(uuid.uuid4(), "user_friend", session)

    assert error.value.status_code == 404
