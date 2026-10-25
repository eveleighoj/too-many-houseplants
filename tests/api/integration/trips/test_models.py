from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from api.trips.models import Booking, Place, Stay, Stop, Trip, TripDay


def count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def booking(session, reference: str) -> Booking:
    return session.scalar(select(Booking).where(Booking.reference == reference))


class TestTrip:
    def test_delete_cascades_to_days_stops_stays_and_bookings(self, session, saved_trip):
        session.delete(session.get(Trip, saved_trip.id))
        session.commit()

        assert [count(session, m) for m in (Trip, TripDay, Stop, Stay, Booking)] == [0] * 5

    def test_delete_keeps_the_owners_places(self, session, saved_trip):
        places = count(session, Place)

        session.delete(session.get(Trip, saved_trip.id))
        session.commit()

        assert count(session, Place) == places

    def test_insert_defaults_id_and_created_at(self, session, owner_id):
        trip = Trip(owner_id=owner_id, title="Wales")
        session.add(trip)
        session.flush()

        assert trip.id is not None
        assert trip.created_at is not None


class TestPlace:
    def test_delete_is_refused_while_a_stop_uses_it(self, session, saved_trip):
        session.delete(session.scalar(select(Place).where(Place.name == "Glencoe")))

        with pytest.raises(IntegrityError):
            session.flush()

    def test_insert_allows_missing_address_and_map_ids(self, session, owner_id):
        place = Place(owner_id=owner_id, name="Somewhere", lat=1.0, lng=2.0)
        session.add(place)
        session.flush()

        assert (place.address, place.google_place_id, place.apple_place_id) == (None, None, None)


class TestTripDay:
    def test_insert_rejects_duplicate_day_number_in_a_trip(self, session, saved_trip):
        session.add(TripDay(trip_id=saved_trip.id, day_number=1, date=date(2026, 6, 9)))

        with pytest.raises(IntegrityError):
            session.flush()


class TestStay:
    @pytest.mark.parametrize("first_night, nights", [(0, 1), (1, 0)])
    def test_insert_rejects_non_positive_nights(self, session, saved_trip, first_night, nights):
        place_id = session.scalar(select(Place.id).limit(1))
        session.add(
            Stay(trip_id=saved_trip.id, place_id=place_id, first_night=first_night, nights=nights)
        )

        with pytest.raises(IntegrityError):
            session.flush()


class TestBooking:
    def test_insert_rejects_being_for_both_a_stop_and_a_stay(self, session, saved_trip):
        stop_booking = booking(session, "ABC123")
        stop_booking.stay_id = booking(session, "HOTEL-1").stay_id

        with pytest.raises(IntegrityError):
            session.flush()

    def test_insert_allows_being_for_neither_a_stop_nor_a_stay(self, session, saved_trip):
        place_id = session.scalar(select(Place.id).limit(1))
        session.add(Booking(trip_id=saved_trip.id, place_id=place_id, reference="FERRY"))
        session.flush()

        assert booking(session, "FERRY").stop_id is None

    def test_deleting_its_stop_keeps_the_booking_unattached(self, session, saved_trip):
        stop_id = booking(session, "ABC123").stop_id
        session.delete(session.get(Stop, stop_id))
        session.commit()
        session.expire_all()

        remaining = booking(session, "ABC123")
        assert remaining is not None
        assert remaining.stop_id is None

    def test_deleting_its_stay_keeps_the_booking_unattached(self, session, saved_trip):
        stay_id = booking(session, "HOTEL-1").stay_id
        session.delete(session.get(Stay, stay_id))
        session.commit()
        session.expire_all()

        assert booking(session, "HOTEL-1").stay_id is None
