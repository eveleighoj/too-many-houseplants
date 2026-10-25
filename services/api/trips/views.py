"""Response shapes, and the pure transformation from ORM rows into them.

No I/O and no access decisions here (those are in access.py), which is what makes it cheap
to unit test thoroughly.
"""

import datetime as dt
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from api.trips.models import Booking, Place, Stay, Stop, Trip, TripDay


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
    date: dt.date
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
    stays: list[StayView]
    bookings: list[BookingView]


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


def build_trip_view(trip: Trip) -> TripView:
    return TripView(
        id=str(trip.id),
        title=trip.title,
        days=[build_trip_day_view(day) for day in trip.days],
        stays=[build_stay_view(stay) for stay in trip.stays],
        bookings=[build_booking_view(booking) for booking in trip.bookings],
    )


def build_trip_day_view(day: TripDay) -> TripDayView:
    return TripDayView(
        day_number=day.day_number,
        date=day.date,
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
