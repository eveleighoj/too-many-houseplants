"""Response shapes, and the pure transformation from ORM rows into them.

Dates, stays and bookings are only included for the trip's owner — day numbers and stops
(with their places) stay visible either way. No I/O and no auth logic here, which is what
makes it cheap to unit test thoroughly.
"""

import datetime as dt
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from houseplants.trips.models import Booking, Place, Stay, Stop, Trip, TripDay


class View(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class PlaceView(View):
    id: str
    name: str
    lat: float
    lng: float
    address: str | None
    google_place_id: str | None
    apple_place_id: str | None
    google_maps_url: str | None
    apple_maps_url: str | None


class StopView(View):
    id: str
    place: PlaceView


class TripDayView(View):
    day_number: int
    date: dt.date | None = None
    stops: list[StopView]


class StayView(View):
    id: str
    place: PlaceView
    first_night: int
    nights: int


class BookingView(View):
    id: str
    place: PlaceView
    stop_id: str | None
    stay_id: str | None
    reference: str | None
    notes: str | None


class TripView(View):
    id: str
    title: str
    days: list[TripDayView]
    # None (not []) for anyone but the owner: "hidden", as opposed to "there aren't any".
    stays: list[StayView] | None
    bookings: list[BookingView] | None


class TripList(View):
    trips: list[TripView]


def google_maps_url(google_place_id: str | None) -> str | None:
    if not google_place_id:
        return None
    return f"https://www.google.com/maps/place/?q=place_id:{quote(google_place_id)}"


def apple_maps_url(apple_place_id: str | None) -> str | None:
    if not apple_place_id:
        return None
    return f"https://maps.apple.com/place?place-id={quote(apple_place_id)}"


def build_place_view(place: Place) -> PlaceView:
    return PlaceView(
        id=str(place.id),
        name=place.name,
        lat=place.lat,
        lng=place.lng,
        address=place.address,
        google_place_id=place.google_place_id,
        apple_place_id=place.apple_place_id,
        google_maps_url=google_maps_url(place.google_place_id),
        apple_maps_url=apple_maps_url(place.apple_place_id),
    )


def build_trip_view(trip: Trip, is_owner: bool) -> TripView:
    return TripView(
        id=str(trip.id),
        title=trip.title,
        days=[build_trip_day_view(day, is_owner) for day in trip.days],
        stays=[build_stay_view(stay) for stay in trip.stays] if is_owner else None,
        bookings=[build_booking_view(booking) for booking in trip.bookings] if is_owner else None,
    )


def build_trip_day_view(day: TripDay, is_owner: bool) -> TripDayView:
    return TripDayView(
        day_number=day.day_number,
        date=day.date if is_owner else None,
        stops=[build_stop_view(stop) for stop in day.stops],
    )


def build_stop_view(stop: Stop) -> StopView:
    return StopView(id=str(stop.id), place=build_place_view(stop.place))


def build_stay_view(stay: Stay) -> StayView:
    return StayView(
        id=str(stay.id),
        place=build_place_view(stay.place),
        first_night=stay.first_night,
        nights=stay.nights,
    )


def build_booking_view(booking: Booking) -> BookingView:
    return BookingView(
        id=str(booking.id),
        place=build_place_view(booking.place),
        stop_id=str(booking.stop_id) if booking.stop_id else None,
        stay_id=str(booking.stay_id) if booking.stay_id else None,
        reference=booking.reference,
        notes=booking.notes,
    )
