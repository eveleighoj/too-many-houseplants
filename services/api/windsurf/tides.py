from datetime import datetime, timedelta

import httpx

from api.windsurf.models import Event, TideDay, TideWindow, UkhoTideEvent

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
MIN_DAYLIGHT = timedelta(minutes=90)


class TidesClient:
    """Client for the UKHO tidal API. `http` must have its base_url set to the API root."""

    def __init__(self, api_key: str, http: httpx.Client):
        self.api_key = api_key
        self.http = http

    def get_week_tides(self, station_id: str, hours_before: int, hours_after: int) -> list[TideDay]:
        response = self.http.get(
            f"/stations/{station_id}/TidalEvents",
            params={"duration": 7},
            headers={"Ocp-Apim-Subscription-Key": self.api_key},
        )
        response.raise_for_status()
        events = [UkhoTideEvent.model_validate(raw) for raw in response.json()]
        return build_tide_windows(events, hours_before, hours_after)


def get_daylight(date: str) -> tuple[str, str]:
    """Sunrise and sunset for a date.

    Currently hardcoded defaults — replace with a real API call when needed.
    """
    return f"{date}T06:00:00", f"{date}T21:00:00"


def _parse(value: str) -> datetime:
    # UKHO sometimes includes fractional seconds; only whole seconds matter here.
    return datetime.strptime(value[:19], TIME_FORMAT)


def build_tide_windows(
    events: list[UkhoTideEvent], hours_before: int, hours_after: int
) -> list[TideDay]:
    days: dict[str, TideDay] = {}

    for i, event in enumerate(events):
        if event.EventType != "HighWater":
            continue

        date = event.DateTime.split("T")[0]
        high_time = _parse(event.DateTime)
        windsurf_start = high_time - timedelta(hours=hours_before)
        windsurf_end = high_time + timedelta(hours=hours_after)

        if date not in days:
            sunrise, sunset = get_daylight(date)
            days[date] = TideDay(date=date, sunrise=sunrise, sunset=sunset)
        day = days[date]

        overlap_start = max(windsurf_start, _parse(day.sunrise))
        overlap_end = min(windsurf_end, _parse(day.sunset))
        acceptable = overlap_end - overlap_start >= MIN_DAYLIGHT

        window_events: list[Event] = []
        if i > 0 and events[i - 1].EventType == "LowWater":
            window_events.append(_tide_event(events[i - 1]))
        window_events.append(
            Event(type="WindsurfStart", date_time=windsurf_start.strftime(TIME_FORMAT))
        )
        window_events.append(_tide_event(event))
        window_events.append(
            Event(type="WindsurfEnd", date_time=windsurf_end.strftime(TIME_FORMAT))
        )
        if i < len(events) - 1 and events[i + 1].EventType == "LowWater":
            window_events.append(_tide_event(events[i + 1]))

        day.windows.append(TideWindow(acceptable=acceptable, events=window_events))

    return [days[date] for date in sorted(days)]


def _tide_event(event: UkhoTideEvent) -> Event:
    return Event(type=event.EventType, date_time=event.DateTime, height=event.Height)
