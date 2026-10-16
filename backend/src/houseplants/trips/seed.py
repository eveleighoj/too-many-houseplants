"""Local demo trips. Run via `make seed` (houseplants.seed), never in production.

Every row gets a fixed id (see houseplants.common.seeding), numbered under its trip so an id
says what it is — e.g. trip 1 is 00000002-…-000000000001 and its day 2 is 00000004-…-000000000102.
"""

import uuid
from collections import Counter
from datetime import date, timedelta

from sqlalchemy import delete, or_
from sqlalchemy.orm import Session

from houseplants.common.seeding import seed_id
from houseplants.trips.models import Booking, Place, Stay, Stop, Trip, TripDay

# Id kinds (the first block of the uuid). 1 was users, before they moved to Clerk.
TRIP_KIND = 2  # trip N:                    N
PLACE_KIND = 3  # Nth place of trip T:       T*100 + N
DAY_KIND = 4  # day D of trip T:             T*100 + D
STOP_KIND = 5  # stop S of day D of trip T:  T*10000 + D*100 + S
STAY_KIND = 6  # Nth stay of trip T:         T*100 + N
BOOKING_KIND = 7  # Nth booking of trip T:   T*100 + N


class TripSeed:
    """Builds one seed trip with fixed ids. Create its places first, then call `trip()`, then
    add stays and bookings — numbered in the order they're added."""

    def __init__(self, number: int, owner_id: str):
        self.number = number
        self.owner_id = owner_id
        self.places: list[Place] = []
        self.trip_row: Trip | None = None
        self._added: Counter[int] = Counter()

    def _next_id(self, kind: int) -> uuid.UUID:
        self._added[kind] += 1
        return seed_id(kind, self.number * 100 + self._added[kind])

    def place(self, name: str, lat: float, lng: float, address: str | None = None) -> Place:
        place = Place(
            id=self._next_id(PLACE_KIND),
            owner_id=self.owner_id,
            name=name,
            lat=lat,
            lng=lng,
            address=address,
        )
        self.places.append(place)
        return place

    def trip(self, title: str, start: date, days: list[list[Place]]) -> Trip:
        """The trip itself: day N is `start` + N-1 days, visiting its places in order."""
        self.trip_row = Trip(
            id=seed_id(TRIP_KIND, self.number),
            owner_id=self.owner_id,
            title=title,
            days=[
                TripDay(
                    id=seed_id(DAY_KIND, self.number * 100 + day_number),
                    day_number=day_number,
                    date=start + timedelta(days=day_number - 1),
                    stops=[
                        Stop(
                            id=seed_id(STOP_KIND, self.number * 10000 + day_number * 100 + order),
                            sort_order=order,
                            place=place,
                        )
                        for order, place in enumerate(places, start=1)
                    ],
                )
                for day_number, places in enumerate(days, start=1)
            ],
            stays=[],
            bookings=[],
        )
        return self.trip_row

    def stay(self, place: Place, first_night: int, nights: int) -> Stay:
        stay = Stay(
            id=self._next_id(STAY_KIND), place=place, first_night=first_night, nights=nights
        )
        self.trip_row.stays.append(stay)
        return stay

    def booking(
        self,
        place: Place,
        reference: str,
        notes: str | None = None,
        stop: Stop | None = None,
        stay: Stay | None = None,
    ) -> Booking:
        booking = Booking(
            id=self._next_id(BOOKING_KIND),
            place=place,
            reference=reference,
            notes=notes,
            stop=stop,
            stay=stay,
        )
        self.trip_row.bookings.append(booking)
        return booking

    def stop_at(self, place: Place) -> Stop:
        return next(stop for day in self.trip_row.days for stop in day.stops if stop.place is place)


def build_seed_trips(demo_owner_id: str, friend_owner_id: str, today: date) -> list[TripSeed]:
    """The demo trips, unsaved. Dates are relative to `today` so they always look upcoming."""
    # --- 1. demo: Scottish Highlands ----------------------------------------------------
    s = TripSeed(1, demo_owner_id)
    glasgow = s.place("Glasgow", 55.8642, -4.2518)
    loch_lomond = s.place("Loch Lomond (Balloch)", 56.0035, -4.5833)
    glencoe = s.place("Glencoe", 56.6826, -5.1023)
    clachaig = s.place("Clachaig Inn", 56.6716, -5.0571, "Glencoe, Ballachulish PH49 4HX")
    fort_william = s.place("Fort William", 56.8198, -5.1052)
    glenfinnan = s.place("Glenfinnan Viaduct", 56.8762, -5.4319)
    mallaig = s.place("Mallaig", 57.0059, -5.8287)
    mallaig_hotel = s.place("West Highland Hotel", 57.0063, -5.8301, "Mallaig PH41 4QZ")
    ferry_terminal = s.place("Mallaig Ferry Terminal", 57.0068, -5.8277, "Mallaig PH41 4QD")
    armadale = s.place("Armadale", 57.0646, -5.8944)
    portree = s.place("Portree", 57.4125, -6.1964)
    portree_hotel = s.place("Portree Hotel", 57.4130, -6.1950, "Somerled Square, Portree IV51 9EH")
    storr = s.place("Old Man of Storr", 57.5074, -6.1826)
    quiraing = s.place("Quiraing", 57.6286, -6.2884)

    s.trip(
        "Scottish Highlands road trip",
        today + timedelta(days=30),
        [
            [glasgow, loch_lomond, glencoe],
            [fort_william, glenfinnan, mallaig],
            [armadale, portree],
            [storr, quiraing],
        ],
    )
    clachaig_stay = s.stay(clachaig, first_night=1, nights=1)
    s.stay(mallaig_hotel, first_night=2, nights=1)
    portree_stay = s.stay(portree_hotel, first_night=3, nights=2)
    s.booking(clachaig, "CLA-48213", "Check-in from 3pm", stay=clachaig_stay)
    s.booking(portree_hotel, "SKY-2290", stay=portree_stay)
    s.booking(
        glenfinnan,
        "JAC-3301",
        "Jacobite steam train, 10:15 departure",
        stop=s.stop_at(glenfinnan),
    )
    # Not for any stop or stay: the ferry is how you get from day 2 to day 3.
    s.booking(ferry_terminal, "CMAL-7781", "Ferry to Armadale, arrive 30 mins early")
    highlands = s

    # --- 2. demo: Lake District ---------------------------------------------------------
    s = TripSeed(2, demo_owner_id)
    windermere = s.place("Windermere", 54.3800, -2.9070)
    grasmere = s.place("Grasmere", 54.4587, -3.0244)
    yha = s.place("YHA Ambleside", 54.4220, -2.9640, "Waterhead, Ambleside LA22 0EU")
    catbells = s.place("Catbells", 54.5683, -3.1700)
    keswick = s.place("Keswick", 54.6013, -3.1347)
    s.trip(
        "Lake District weekend",
        today + timedelta(days=60),
        [[windermere, grasmere], [catbells, keswick]],
    )
    s.booking(yha, "YHA-551023", "Dorm room", stay=s.stay(yha, first_night=1, nights=1))
    lakes = s

    # --- 3. demo: nothing planned yet ---------------------------------------------------
    japan = TripSeed(3, demo_owner_id)
    japan.trip("Japan (still planning)", today + timedelta(days=200), [])

    # --- 4. friend: only ever seen redacted by the demo user ----------------------------
    s = TripSeed(4, friend_owner_id)
    fistral = s.place("Fistral Beach, Newquay", 50.4176, -5.1006)
    fistral_hotel = s.place("Headland Hotel", 50.4188, -5.0987, "Headland Rd, Newquay TR7 1EW")
    st_ives = s.place("St Ives", 50.2110, -5.4800)
    s.trip("Cornwall surf trip", today + timedelta(days=14), [[fistral], [st_ives]])
    s.stay(fistral_hotel, first_night=1, nights=1)
    s.booking(fistral, "FIS-1102", "Board hire", stop=s.stop_at(fistral))
    cornwall = s

    return [highlands, lakes, japan, cornwall]


def seed_trips(
    session: Session, demo_owner_id: str, friend_owner_id: str, today: date
) -> list[Trip]:
    """Replaces every trip and place owned by the two seed owners — or using a seed id —
    with the demo set."""
    seeds = build_seed_trips(demo_owner_id, friend_owner_id, today)
    owners = [demo_owner_id, friend_owner_id]
    trip_ids = [seed.trip_row.id for seed in seeds]
    place_ids = [place.id for seed in seeds for place in seed.places]

    # Trips first: deleting them cascades to their days, stops, stays and bookings, which
    # frees their places to be deleted.
    session.execute(delete(Trip).where(or_(Trip.owner_id.in_(owners), Trip.id.in_(trip_ids))))
    session.execute(delete(Place).where(or_(Place.owner_id.in_(owners), Place.id.in_(place_ids))))

    trips = [seed.trip_row for seed in seeds]
    session.add_all(trips)
    session.commit()
    return trips
