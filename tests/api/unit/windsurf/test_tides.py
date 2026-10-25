import httpx
import pytest

from api.windsurf.models import UkhoTideEvent
from api.windsurf.tides import TidesClient, build_tide_windows, get_daylight


def high_water(date_time: str, height: float) -> UkhoTideEvent:
    return UkhoTideEvent(EventType="HighWater", DateTime=date_time, Height=height)


def low_water(date_time: str, height: float) -> UkhoTideEvent:
    return UkhoTideEvent(EventType="LowWater", DateTime=date_time, Height=height)


def ukho_client(handler) -> httpx.Client:
    return httpx.Client(base_url="https://ukho.test", transport=httpx.MockTransport(handler))


def test_get_daylight_returns_fixed_sunrise_and_sunset():
    assert get_daylight("2026-06-01") == ("2026-06-01T06:00:00", "2026-06-01T21:00:00")


def test_build_tide_windows_acceptable_when_fully_in_daylight():
    days = build_tide_windows([high_water("2026-06-01T12:00:00", 4.5)], 2, 2)

    assert len(days) == 1
    assert len(days[0].windows) == 1
    assert days[0].windows[0].acceptable


def test_build_tide_windows_not_acceptable_when_before_sunrise():
    days = build_tide_windows([high_water("2026-06-01T04:00:00", 4.5)], 1, 1)

    assert not days[0].windows[0].acceptable


def test_build_tide_windows_acceptable_at_exactly_90_minute_boundary():
    # windsurfStart 03:30, windsurfEnd 07:30; sunrise 06:00 -> overlap is exactly 90 minutes.
    days = build_tide_windows([high_water("2026-06-01T04:30:00", 4.5)], 1, 3)

    assert days[0].windows[0].acceptable


def test_build_tide_windows_not_acceptable_just_under_90_minute_boundary():
    # windsurfStart 03:29, windsurfEnd 07:29; sunrise 06:00 -> overlap is 89 minutes.
    days = build_tide_windows([high_water("2026-06-01T04:29:00", 4.5)], 1, 3)

    assert not days[0].windows[0].acceptable


def test_build_tide_windows_includes_neighbouring_low_water_events_in_order():
    events = [
        low_water("2026-06-01T06:00:00", 0.5),
        high_water("2026-06-01T12:00:00", 4.5),
        low_water("2026-06-01T18:00:00", 0.6),
    ]

    window = build_tide_windows(events, 2, 2)[0].windows[0]

    assert [(e.type, e.date_time, e.height) for e in window.events] == [
        ("LowWater", "2026-06-01T06:00:00", 0.5),
        ("WindsurfStart", "2026-06-01T10:00:00", None),
        ("HighWater", "2026-06-01T12:00:00", 4.5),
        ("WindsurfEnd", "2026-06-01T14:00:00", None),
        ("LowWater", "2026-06-01T18:00:00", 0.6),
    ]


def test_build_tide_windows_groups_by_day_in_date_order():
    events = [
        high_water("2026-06-02T12:00:00", 4.4),
        high_water("2026-06-01T00:30:00", 4.1),
        high_water("2026-06-01T13:00:00", 4.5),
    ]

    days = build_tide_windows(events, 2, 2)

    assert [day.date for day in days] == ["2026-06-01", "2026-06-02"]
    assert len(days[0].windows) == 2


def test_build_tide_windows_ignores_fractional_seconds():
    days = build_tide_windows([high_water("2026-06-01T12:00:00.123", 4.5)], 2, 2)

    assert days[0].windows[0].events[0].date_time == "2026-06-01T10:00:00"


def test_build_tide_windows_ignores_low_water_without_a_high_water():
    assert build_tide_windows([low_water("2026-06-01T06:00:00", 0.5)], 2, 2) == []


class TestTidesClient:
    def test_get_week_tides_calls_ukho_with_subscription_key(self):
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(
                200,
                json=[{"EventType": "HighWater", "DateTime": "2026-06-01T12:00:00", "Height": 4.5}],
            )

        TidesClient("secret-key", ukho_client(handler)).get_week_tides("0110", 2, 2)

        assert seen[0].url.path == "/stations/0110/TidalEvents"
        assert seen[0].url.params["duration"] == "7"
        assert seen[0].headers["Ocp-Apim-Subscription-Key"] == "secret-key"

    def test_get_week_tides_builds_windows_from_response(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json=[{"EventType": "HighWater", "DateTime": "2026-06-01T12:00:00", "Height": 4.5}],
            )

        days = TidesClient("secret-key", ukho_client(handler)).get_week_tides("0110", 2, 2)

        assert days[0].date == "2026-06-01"
        assert days[0].windows[0].acceptable

    def test_get_week_tides_raises_on_error_status(self):
        client = TidesClient("secret-key", ukho_client(lambda _: httpx.Response(500)))

        with pytest.raises(httpx.HTTPStatusError):
            client.get_week_tides("0110", 2, 2)
