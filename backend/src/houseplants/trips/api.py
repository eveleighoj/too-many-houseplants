import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from houseplants.common.db import get_session
from houseplants.common.docs import SWAGGER_UI_PARAMETERS, api_description
from houseplants.common.security import OptionalUserId, UserId
from houseplants.trips.models import Booking, Stay, Stop, Trip, TripDay
from houseplants.trips.views import TripList, TripView, build_trip_view

app = FastAPI(
    title="Trips API",
    version="1.0.0",
    description=api_description(
        "Trip itineraries. Listing and creating trips needs a bearer token; anyone can get a "
        "trip, but dates, stays and bookings are only shown to its owner."
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
    return build_trip_view(trip, is_owner=True)  # the creator is always the owner


@app.get("/", summary="List your own trips", tags=["Trips"])
def list_trips(user_id: UserId, session: DbSession) -> TripList:
    trips = session.scalars(
        select(Trip)
        .where(Trip.owner_id == user_id)
        .options(*_full_trip)
        .order_by(Trip.created_at.desc())
    )
    return TripList(trips=[build_trip_view(trip, is_owner=True) for trip in trips])


@app.get(
    "/{trip_id}",
    summary="Get a trip — full detail if you're the owner, redacted otherwise",
    tags=["Trips"],
)
def get_trip(trip_id: uuid.UUID, user_id: OptionalUserId, session: DbSession) -> TripView:
    trip = session.scalar(select(Trip).where(Trip.id == trip_id).options(*_full_trip))
    if trip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="trip not found")
    return build_trip_view(trip, is_owner=user_id == str(trip.owner_id))
