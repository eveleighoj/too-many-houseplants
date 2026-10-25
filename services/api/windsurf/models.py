from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


@dataclass(frozen=True)
class Spot:
    station_id: str
    hours_before: int
    hours_after: int


KNOWN_SPOTS: dict[str, Spot] = {
    "chalkwell": Spot(station_id="0110", hours_before=2, hours_after=2),
    "uncle-toms": Spot(station_id="0110", hours_before=2, hours_after=4),
}


class UkhoTideEvent(BaseModel):
    """The raw response shape from the UKHO API."""

    EventType: str
    DateTime: str
    Height: float


class View(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Event(View):
    """A single entry in a tide window. Height is absent for WindsurfStart/WindsurfEnd."""

    type: str
    date_time: str
    height: float | None = None


class TideWindow(View):
    """A high tide and its surrounding context, ordered by time.

    acceptable is true if the window contains at least 90 minutes of daylight
    (30 minute rigging buffer + 60 minutes of surfing).
    """

    acceptable: bool
    events: list[Event]


class TideDay(View):
    date: str
    sunrise: str
    sunset: str
    windows: list[TideWindow] = []


class SpotTides(View):
    spot: str
    days: list[TideDay]
