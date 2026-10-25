import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from api.common.db import get_session
from api.common.docs import SWAGGER_UI_PARAMETERS, api_description
from api.common.security import UserId
from api.trips.access import can_view, visible_trips
from api.trips.models import Booking, Stay, Stop, Trip, TripDay
from api.trips.views import TripList, TripView, build_trip_view

app = FastAPI(
    title="Trips API",
    version="1.0.0",
    description=api_description(
        "Trip itineraries. Every endpoint needs a bearer token; any signed-in user can see "
        "every trip (see docs/trips.md)."
    ),
    swagger_ui_parameters=SWAGGER_UI_PARAMETERS,
)

DbSession = Annotated[Session, Depends(get_session)]

# Loads a trip's whole tree (days → stops, stays, bookings, and their places) in a fixed
# number of queries.
_full_trip = [
    selectinload(Trip.days).selectinload(TripDay.stops).selectinload(Stop.place),
    selectinload(Trip.stays).selectinload(Stay.place),
    selectinload(Trip.bookings).selectinload(Booking.place),
]


class CreateTrip(BaseModel):
    title: str = Field(min_length=1, description="Trip title")


@app.post("/", status_code=status.HTTP_201_CREATED, summary="Create a trip", tags=["Trips"])
def create_trip(body: CreateTrip, user_id: UserId, session: DbSession) -> TripView:
    trip = Trip(owner_id=user_id, title=body.title, days=[])
    session.add(trip)
    session.commit()
    return build_trip_view(trip)


@app.get("/", summary="List the trips you can see, newest first", tags=["Trips"])
def list_trips(user_id: UserId, session: DbSession) -> TripList:
    trips = session.scalars(
        select(Trip)
        .where(visible_trips(user_id))
        .options(*_full_trip)
        .order_by(Trip.created_at.desc())
    )
    return TripList(trips=[build_trip_view(trip) for trip in trips])


@app.get("/{trip_id}", summary="Get a trip", tags=["Trips"])
def get_trip(trip_id: uuid.UUID, user_id: UserId, session: DbSession) -> TripView:
    trip = session.scalar(select(Trip).where(Trip.id == trip_id).options(*_full_trip))
    # A trip you can't see is "not found", so its existence isn't revealed either.
    if trip is None or not can_view(user_id, trip):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="trip not found")
    return build_trip_view(trip)
