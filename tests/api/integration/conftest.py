from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from api.trips.models import Booking, Place, Stay, Stop, Trip, TripDay


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    engine = create_engine(database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A session whose changes — including commits made by the code under test — are rolled
    back at the end of the test, so integration tests never see each other's data."""
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def owner_id(user_id) -> str:
    return user_id


@pytest.fixture
def saved_trip(session, owner_id) -> Trip:
    """Two days (stored out of order, to check ordering), one stay, and two bookings: one for
    a stop and one for the stay."""

    def place(name: str) -> Place:
        return Place(owner_id=owner_id, name=name, lat=56.8, lng=-5.1)

    spean_bridge, hotel = place("Spean Bridge"), place("Spean Bridge Hotel")
    spean_stop = Stop(sort_order=0, place=spean_bridge)
    stay = Stay(place=hotel, first_night=1, nights=2)
    trip = Trip(
        owner_id=owner_id,
        title="Scotland",
        days=[
            TripDay(
                day_number=2,
                date=date(2026, 6, 2),
                stops=[Stop(sort_order=0, place=place("Glencoe"))],
            ),
            TripDay(
                day_number=1,
                date=date(2026, 6, 1),
                stops=[Stop(sort_order=1, place=place("Fort William")), spean_stop],
            ),
        ],
        stays=[stay],
        bookings=[
            Booking(place=spean_bridge, stop=spean_stop, reference="ABC123"),
            Booking(place=hotel, stay=stay, reference="HOTEL-1"),
        ],
    )
    session.add(trip)
    session.commit()
    session.refresh(trip)  # load id/owner_id before detaching, so tests can read them
    # Start each test from a clean identity map, so reads really come from the database.
    session.expunge_all()
    return trip
