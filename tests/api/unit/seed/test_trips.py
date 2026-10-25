from datetime import date

import pytest

from scripts.api.seed.ids import seed_id
from scripts.api.seed.trips import (
    BOOKING_KIND,
    DAY_KIND,
    PLACE_KIND,
    STAY_KIND,
    STOP_KIND,
    TRIP_KIND,
    TripSeed,
    build_seed_trips,
)

START = date(2026, 6, 1)


def make_seed(number: int = 1) -> TripSeed:
    return TripSeed(number, "user_owner")


class TestTripSeed:
    def test_place_numbers_places_under_the_trip(self):
        seed = make_seed(2)

        first, second = seed.place("A", 1.0, 2.0), seed.place("B", 3.0, 4.0)

        assert (first.id, second.id) == (seed_id(PLACE_KIND, 201), seed_id(PLACE_KIND, 202))
        assert first.owner_id == seed.owner_id

    def test_trip_uses_the_trip_number_as_its_id(self):
        seed = make_seed(3)

        assert seed.trip("Trip", START, []).id == seed_id(TRIP_KIND, 3)

    def test_trip_numbers_and_dates_days_from_start(self):
        trip = make_seed(1).trip("Trip", START, [[], [], []])

        assert [(day.id, day.day_number, day.date) for day in trip.days] == [
            (seed_id(DAY_KIND, 101), 1, date(2026, 6, 1)),
            (seed_id(DAY_KIND, 102), 2, date(2026, 6, 2)),
            (seed_id(DAY_KIND, 103), 3, date(2026, 6, 3)),
        ]

    def test_trip_makes_a_stop_per_place_numbered_by_day_and_order(self):
        seed = make_seed(1)
        a, b = seed.place("A", 1.0, 2.0), seed.place("B", 3.0, 4.0)

        trip = seed.trip("Trip", START, [[], [a, b]])

        assert [(stop.id, stop.sort_order, stop.place) for stop in trip.days[1].stops] == [
            (seed_id(STOP_KIND, 10201), 1, a),
            (seed_id(STOP_KIND, 10202), 2, b),
        ]

    def test_stay_and_booking_are_added_to_the_trip_with_numbered_ids(self):
        seed = make_seed(4)
        place = seed.place("Hotel", 1.0, 2.0)
        seed.trip("Trip", START, [])

        stay = seed.stay(place, first_night=1, nights=2)
        booking = seed.booking(place, "REF", stay=stay)

        assert seed.trip_row.stays == [stay]
        assert seed.trip_row.bookings == [booking]
        assert (stay.id, booking.id) == (seed_id(STAY_KIND, 401), seed_id(BOOKING_KIND, 401))

    def test_stop_at_finds_the_stop_for_a_place(self):
        seed = make_seed()
        a, b = seed.place("A", 1.0, 2.0), seed.place("B", 3.0, 4.0)
        trip = seed.trip("Trip", START, [[a], [b]])

        assert seed.stop_at(b) is trip.days[1].stops[0]

    def test_stop_at_raises_for_a_place_not_visited(self):
        seed = make_seed()
        seed.trip("Trip", START, [[seed.place("A", 1.0, 2.0)]])

        with pytest.raises(StopIteration):
            seed.stop_at(seed.place("elsewhere", 0.0, 0.0))


def test_build_seed_trips_gives_the_same_ids_every_time():
    demo, friend = "user_demo", "user_friend"

    def all_ids(seeds):
        return [
            (row.id)
            for seed in seeds
            for row in [
                seed.trip_row,
                *seed.places,
                *seed.trip_row.days,
                *(stop for day in seed.trip_row.days for stop in day.stops),
                *seed.trip_row.stays,
                *seed.trip_row.bookings,
            ]
        ]

    first = all_ids(build_seed_trips(demo, friend, START))
    second = all_ids(build_seed_trips("user_a", "user_b", date(2030, 1, 1)))

    assert first == second
    assert len(set(first)) == len(first)  # and no two rows share one


def test_build_seed_trips_numbers_trips_from_one():
    seeds = build_seed_trips("user_a", "user_b", START)

    assert [seed.trip_row.id for seed in seeds] == [seed_id(TRIP_KIND, n) for n in (1, 2, 3, 4)]
    assert seeds[0].trip_row.title == "Scottish Highlands road trip"
