import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, MetaData, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

SCHEMA = "trips"


class Base(DeclarativeBase):
    metadata = MetaData(
        schema=SCHEMA,
        # Postgres's own default names, so Alembic always knows a constraint's name (needed to
        # drop it in a migration) and the constraints created before this was added still match.
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "pk": "%(table_name)s_pkey",
            "fk": "%(table_name)s_%(column_0_N_name)s_fkey",
            "uq": "%(table_name)s_%(column_0_N_name)s_key",
            "ck": "%(table_name)s_%(constraint_name)s",
        },
    )


class Place(Base):
    """Somewhere on the map. Every stop, stay and booking points at one — places hold all of
    the trips sub-app's geographic data. Owned per user, so private places never leak and
    editing one never affects anyone else's trips."""

    __tablename__ = "places"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    # The bearer token's `sub` (a Clerk user id) of the user who owns it, like Trip.owner_id.
    owner_id: Mapped[str] = mapped_column(index=True)
    name: Mapped[str]
    lat: Mapped[float]
    lng: Mapped[float]
    address: Mapped[str | None]
    # Ids for finding the place in Google Maps / Apple Maps; the API turns them into links.
    google_place_id: Mapped[str | None]
    apple_place_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    # The bearer token's `sub` of whoever created it: a Clerk user id like "user_2ab…".
    # Users live in Clerk, not our database, so there's nothing to reference.
    owner_id: Mapped[str] = mapped_column(index=True)
    title: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    days: Mapped[list["TripDay"]] = relationship(
        back_populates="trip", order_by="TripDay.day_number", cascade="all, delete-orphan"
    )
    stays: Mapped[list["Stay"]] = relationship(
        back_populates="trip", order_by="Stay.first_night", cascade="all, delete-orphan"
    )
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan"
    )


class TripDay(Base):
    __tablename__ = "trip_days"
    __table_args__ = (UniqueConstraint("trip_id", "day_number"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    trip_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trips.trips.id", ondelete="CASCADE"))
    day_number: Mapped[int]
    date: Mapped[date]

    trip: Mapped[Trip] = relationship(back_populates="days")
    stops: Mapped[list["Stop"]] = relationship(
        back_populates="day", order_by="Stop.sort_order", cascade="all, delete-orphan"
    )


class Stop(Base):
    __tablename__ = "stops"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    trip_day_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.trip_days.id", ondelete="CASCADE")
    )
    sort_order: Mapped[int]
    # RESTRICT: a place can't be deleted while anything still points at it.
    place_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.places.id", ondelete="RESTRICT"), index=True
    )

    day: Mapped[TripDay] = relationship(back_populates="stops")
    place: Mapped[Place] = relationship()


class Stay(Base):
    """Where you sleep: one place for `nights` consecutive nights, starting on the night of
    day `first_night` (e.g. first_night=3, nights=2 covers the nights of days 3 and 4)."""

    __tablename__ = "stays"
    __table_args__ = (
        CheckConstraint("first_night >= 1", name="first_night_positive"),
        CheckConstraint("nights >= 1", name="nights_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    trip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.trips.id", ondelete="CASCADE"), index=True
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.places.id", ondelete="RESTRICT"), index=True
    )
    first_night: Mapped[int]
    nights: Mapped[int]

    trip: Mapped[Trip] = relationship(back_populates="stays")
    place: Mapped[Place] = relationship()


class Booking(Base):
    """A reservation on a trip — always at a place, and optionally for one stop or stay
    (e.g. the hotel booking for a stay, or a ferry that isn't a stop at all)."""

    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("num_nonnulls(stop_id, stay_id) <= 1", name="for_one_stop_or_stay"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    trip_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.trips.id", ondelete="CASCADE"), index=True
    )
    place_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trips.places.id", ondelete="RESTRICT"), index=True
    )
    # Removing the stop or stay keeps the booking, just no longer attached to it.
    stop_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trips.stops.id", ondelete="SET NULL"), index=True
    )
    stay_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("trips.stays.id", ondelete="SET NULL"), index=True
    )
    reference: Mapped[str | None]
    notes: Mapped[str | None]

    trip: Mapped[Trip] = relationship(back_populates="bookings")
    place: Mapped[Place] = relationship()
    stop: Mapped[Stop | None] = relationship()
    stay: Mapped[Stay | None] = relationship()
