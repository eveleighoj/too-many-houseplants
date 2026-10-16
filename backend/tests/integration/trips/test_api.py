import uuid

import pytest
from fastapi import HTTPException

from houseplants.trips.api import CreateTrip, create_trip, get_trip, list_trips
from houseplants.trips.models import Trip


def test_create_trip_saves_trip_owned_by_the_caller(session, owner_id):
    view = create_trip(CreateTrip(title="Wales"), str(owner_id), session)

    saved = session.get(Trip, uuid.UUID(view.id))
    assert saved.owner_id == owner_id
    assert saved.title == "Wales"


def test_create_trip_returns_owner_view_with_nothing_planned(session, owner_id):
    view = create_trip(CreateTrip(title="Wales"), str(owner_id), session)

    assert view.title == "Wales"
    assert (view.days, view.stays, view.bookings) == ([], [], [])


def test_list_trips_returns_only_the_callers_trips(session, saved_trip):
    create_trip(CreateTrip(title="Someone else's"), str(uuid.uuid4()), session)

    result = list_trips(str(saved_trip.owner_id), session)

    assert [trip.title for trip in result.trips] == ["Scotland"]


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


def test_list_trips_returns_owner_view(session, saved_trip):
    result = list_trips(str(saved_trip.owner_id), session)

    assert result.trips[0].days[0].date is not None


def test_get_trip_returns_days_and_stops_in_order(session, saved_trip):
    view = get_trip(saved_trip.id, None, session)

    assert [day.day_number for day in view.days] == [1, 2]
    assert [stop.place.name for stop in view.days[0].stops] == ["Spean Bridge", "Fort William"]


def test_get_trip_returns_full_detail_to_the_owner(session, saved_trip):
    view = get_trip(saved_trip.id, str(saved_trip.owner_id), session)

    assert view.days[0].date is not None
    assert [(stay.place.name, stay.nights) for stay in view.stays] == [("Spean Bridge Hotel", 2)]
    bookings = {booking.reference: booking for booking in view.bookings}
    assert bookings["ABC123"].stop_id == view.days[0].stops[0].id
    assert bookings["HOTEL-1"].stay_id == view.stays[0].id


@pytest.mark.parametrize("caller", [None, str(uuid.uuid4())], ids=["anonymous", "other-user"])
def test_get_trip_redacts_for_anyone_but_the_owner(session, saved_trip, caller):
    view = get_trip(saved_trip.id, caller, session)

    assert all(day.date is None for day in view.days)
    assert (view.stays, view.bookings) == (None, None)
    assert [stop.place.name for stop in view.days[0].stops] == ["Spean Bridge", "Fort William"]


def test_get_trip_raises_404_for_unknown_trip(session):
    with pytest.raises(HTTPException) as error:
        get_trip(uuid.uuid4(), None, session)

    assert error.value.status_code == 404
