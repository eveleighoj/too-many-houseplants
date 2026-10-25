import uuid
from datetime import date

import pytest

from api.trips.models import Booking, Place, Stay, Stop, Trip, TripDay
from api.trips.views import (
    apple_maps_url,
    build_booking_view,
    build_place_view,
    build_stay_view,
    build_stop_view,
    build_trip_day_view,
    build_trip_view,
    google_maps_url,
)


def make_place(name="Glencoe", **fields) -> Place:
    return Place(id=uuid.uuid4(), name=name, lat=56.68, lng=-5.10, **fields)


def make_trip() -> Trip:
    glencoe, inn = make_place("Glencoe"), make_place("Clachaig Inn")
    stop = Stop(id=uuid.uuid4(), sort_order=0, place=glencoe)
    stay = Stay(id=uuid.uuid4(), place=inn, first_night=1, nights=2)
    return Trip(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        title="Scotland",
        days=[TripDay(day_number=1, date=date(2026, 6, 1), stops=[stop])],
        stays=[stay],
        bookings=[
            Booking(id=uuid.uuid4(), place=inn, stay_id=stay.id, reference="ABC123", notes="late")
        ],
    )


def test_google_maps_url_links_to_the_place_id():
    assert google_maps_url("ChIJ123") == "https://www.google.com/maps/place/?q=place_id:ChIJ123"


def test_google_maps_url_escapes_the_id():
    assert google_maps_url("a b/c") == "https://www.google.com/maps/place/?q=place_id:a%20b/c"


@pytest.mark.parametrize("place_id", [None, ""])
def test_google_maps_url_is_none_without_an_id(place_id):
    assert google_maps_url(place_id) is None


def test_apple_maps_url_links_to_the_place_id():
    assert apple_maps_url("I63802885C8189B2B") == (
        "https://maps.apple.com/place?place-id=I63802885C8189B2B"
    )


@pytest.mark.parametrize("place_id", [None, ""])
def test_apple_maps_url_is_none_without_an_id(place_id):
    assert apple_maps_url(place_id) is None


def test_build_place_view_includes_details_and_map_links():
    place = make_place(address="PH49 4HX", google_place_id="ChIJ123", apple_place_id="IABC")

    view = build_place_view(place)

    assert view.id == str(place.id)
    assert (view.name, view.lat, view.lng, view.address) == ("Glencoe", 56.68, -5.10, "PH49 4HX")
    assert (view.google_place_id, view.apple_place_id) == ("ChIJ123", "IABC")
    assert view.google_maps_url == google_maps_url("ChIJ123")
    assert view.apple_maps_url == apple_maps_url("IABC")


def test_build_place_view_has_no_links_without_ids():
    view = build_place_view(make_place())

    assert (view.google_maps_url, view.apple_maps_url) == (None, None)


def test_build_trip_view_includes_days_stays_and_bookings():
    trip = make_trip()

    view = build_trip_view(trip)

    assert view.id == str(trip.id)
    assert view.title == "Scotland"
    assert [stop.place.name for stop in view.days[0].stops] == ["Glencoe"]
    assert [stay.place.name for stay in view.stays] == ["Clachaig Inn"]
    assert [booking.reference for booking in view.bookings] == ["ABC123"]


def test_build_trip_view_serialises_with_camel_case_keys():
    body = build_trip_view(make_trip()).model_dump(mode="json", by_alias=True)

    assert body["days"][0]["dayNumber"] == 1
    assert body["stays"][0]["firstNight"] == 1
    assert body["bookings"][0]["stayId"] is not None
    assert "googleMapsUrl" in body["days"][0]["stops"][0]["place"]


def test_build_trip_view_has_empty_lists_for_a_trip_with_nothing_planned():
    view = build_trip_view(
        Trip(id=uuid.uuid4(), owner_id="user_x", title="Japan", days=[], stays=[], bookings=[])
    )

    assert (view.days, view.stays, view.bookings) == ([], [], [])


def test_build_trip_day_view_includes_number_and_date():
    view = build_trip_day_view(make_trip().days[0])

    assert (view.day_number, view.date) == (1, date(2026, 6, 1))


def test_build_stop_view_includes_id_and_place():
    stop = make_trip().days[0].stops[0]

    view = build_stop_view(stop)

    assert view.id == str(stop.id)
    assert view.place.name == "Glencoe"


def test_build_stay_view_includes_place_and_nights():
    stay = make_trip().stays[0]

    view = build_stay_view(stay)

    assert (view.id, view.place.name, view.first_night, view.nights) == (
        str(stay.id),
        "Clachaig Inn",
        1,
        2,
    )


def test_build_booking_view_includes_place_and_what_it_is_for():
    trip = make_trip()

    view = build_booking_view(trip.bookings[0])

    assert view.place.name == "Clachaig Inn"
    assert view.stay_id == str(trip.stays[0].id)
    assert view.stop_id is None
    assert (view.reference, view.notes) == ("ABC123", "late")


def test_build_booking_view_for_neither_stop_nor_stay():
    view = build_booking_view(Booking(id=uuid.uuid4(), place=make_place(), reference="X"))

    assert (view.stop_id, view.stay_id) == (None, None)
