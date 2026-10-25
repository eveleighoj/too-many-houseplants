import uuid
from datetime import date

import pytest

from api.trips.models import Booking, Place, Stay, Stop, Trip, TripDay


@pytest.fixture
def owner_id(user_id) -> str:
    return user_id


@pytest.fixture
def saved_trip(db, owner_id) -> Trip:
    """A stop, a stay, and one booking of each kind: for a stop, for a stay, and for neither.
    One place has Google and Apple ids, so the map links appear in the response."""
    fort_william = Place(
        owner_id=owner_id,
        name="Fort William",
        lat=56.82,
        lng=-5.11,
        address="Fort William PH33",
        google_place_id="ChIJexample",
        apple_place_id="Iexample",
    )
    inn = Place(owner_id=owner_id, name="Clachaig Inn", lat=56.67, lng=-5.06)
    ferry = Place(owner_id=owner_id, name="Mallaig Ferry Terminal", lat=57.01, lng=-5.83)
    stop = Stop(sort_order=0, place=fort_william)
    stay = Stay(place=inn, first_night=1, nights=2)
    trip = Trip(
        owner_id=owner_id,
        title="Scotland",
        days=[TripDay(day_number=1, date=date(2026, 6, 1), stops=[stop])],
        stays=[stay],
        bookings=[
            Booking(place=fort_william, stop=stop, reference="ABC123", notes="late check-in"),
            Booking(place=inn, stay=stay, reference="INN-1"),
            Booking(place=ferry, reference="FERRY-1"),
        ],
    )
    db.add(trip)
    db.commit()
    return trip


def test_create_trip_response_matches_contract(
    client, auth_header, owner_id, assert_matches_schema
):
    response = client.post("/trips/", json={"title": "Wales"}, headers=auth_header(owner_id))

    assert response.status_code == 201
    assert_matches_schema(response.json(), "trips/schemas/trip.json")


def test_create_trip_without_token_matches_error_contract(client, assert_matches_schema):
    response = client.post("/trips/", json={"title": "Wales"})

    assert response.status_code == 401
    assert_matches_schema(response.json(), "common/schemas/error.json")


def test_create_trip_invalid_body_matches_validation_error_contract(
    client, auth_header, owner_id, assert_matches_schema
):
    response = client.post("/trips/", json={"title": ""}, headers=auth_header(owner_id))

    assert response.status_code == 422
    assert_matches_schema(response.json(), "common/schemas/validation-error.json")


def test_list_trips_response_matches_contract(
    client, auth_header, saved_trip, owner_id, assert_matches_schema
):
    response = client.get("/trips/", headers=auth_header(owner_id))

    assert response.status_code == 200
    assert_matches_schema(response.json(), "trips/schemas/trip-list.json")
    assert [trip["id"] for trip in response.json()["trips"]] == [str(saved_trip.id)]


def test_list_trips_includes_other_peoples_trips(
    client, auth_header, saved_trip, assert_matches_schema
):
    response = client.get("/trips/", headers=auth_header("user_friend"))

    assert response.status_code == 200
    assert_matches_schema(response.json(), "trips/schemas/trip-list.json")
    assert [trip["id"] for trip in response.json()["trips"]] == [str(saved_trip.id)]


def test_list_trips_without_token_matches_error_contract(client, assert_matches_schema):
    response = client.get("/trips/")

    assert response.status_code == 401
    assert_matches_schema(response.json(), "common/schemas/error.json")


@pytest.mark.parametrize("caller", ["owner", "friend"])
def test_get_trip_as_any_signed_in_user_matches_contract(
    client, auth_header, saved_trip, owner_id, assert_matches_schema, caller
):
    user_id = owner_id if caller == "owner" else "user_friend"

    response = client.get(f"/trips/{saved_trip.id}", headers=auth_header(user_id))

    assert response.status_code == 200
    assert_matches_schema(response.json(), "trips/schemas/trip.json")
    body = response.json()
    assert {b["reference"] for b in body["bookings"]} == {"ABC123", "INN-1", "FERRY-1"}
    place = body["days"][0]["stops"][0]["place"]
    assert place["googleMapsUrl"] == "https://www.google.com/maps/place/?q=place_id:ChIJexample"
    assert place["appleMapsUrl"] == "https://maps.apple.com/place?place-id=Iexample"


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer not-a-token"}], ids=["no-token", "invalid-token"]
)
def test_get_trip_without_a_valid_token_matches_error_contract(
    client, saved_trip, assert_matches_schema, headers
):
    response = client.get(f"/trips/{saved_trip.id}", headers=headers)

    assert response.status_code == 401
    assert_matches_schema(response.json(), "common/schemas/error.json")


def test_get_trip_unknown_id_matches_error_contract(client, auth_header, assert_matches_schema):
    response = client.get(f"/trips/{uuid.uuid4()}", headers=auth_header("user_friend"))

    assert response.status_code == 404
    assert_matches_schema(response.json(), "common/schemas/error.json")


def test_get_trip_malformed_id_matches_validation_error_contract(
    client, auth_header, assert_matches_schema
):
    response = client.get("/trips/not-a-uuid", headers=auth_header("user_friend"))

    assert response.status_code == 422
    assert_matches_schema(response.json(), "common/schemas/validation-error.json")


def test_openapi_is_published(client):
    response = client.get("/trips/openapi.json")

    assert response.status_code == 200
    assert set(response.json()["paths"]) == {"/", "/{trip_id}"}
