"""The UKHO API is never called: the real TidesClient is given an httpx transport that serves
whatever tide events the test sets up, so everything else runs for real."""

import httpx
import pytest

from api.windsurf.api import app as windsurf_app
from api.windsurf.api import get_tides_client
from api.windsurf.tides import TidesClient


class FakeUkho:
    def __init__(self):
        self.events: list[dict] = []
        self.status_code = 200

    def handle(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(self.status_code, json=self.events)


@pytest.fixture
def ukho() -> FakeUkho:
    fake = FakeUkho()
    http = httpx.Client(base_url="https://ukho.test", transport=httpx.MockTransport(fake.handle))
    windsurf_app.dependency_overrides[get_tides_client] = lambda: TidesClient("test-key", http)
    yield fake
    windsurf_app.dependency_overrides.pop(get_tides_client, None)


def test_get_week_tides_response_matches_contract(client, ukho, assert_matches_schema):
    ukho.events = [
        {"EventType": "LowWater", "DateTime": "2026-06-01T06:00:00", "Height": 0.5},
        {"EventType": "HighWater", "DateTime": "2026-06-01T12:00:00", "Height": 4.5},
        {"EventType": "LowWater", "DateTime": "2026-06-01T18:00:00", "Height": 0.6},
        {"EventType": "HighWater", "DateTime": "2026-06-02T00:30:00.5", "Height": 4.1},
    ]

    response = client.get("/windsurf/tides/chalkwell")

    assert response.status_code == 200
    assert_matches_schema(response.json(), "windsurf/schemas/spot-tides.json")
    assert [day["date"] for day in response.json()["days"]] == ["2026-06-01", "2026-06-02"]


def test_get_week_tides_with_no_events_matches_contract(client, ukho, assert_matches_schema):
    response = client.get("/windsurf/tides/chalkwell")

    assert response.status_code == 200
    assert_matches_schema(response.json(), "windsurf/schemas/spot-tides.json")
    assert response.json()["days"] == []


def test_get_week_tides_unknown_spot_matches_error_contract(client, ukho, assert_matches_schema):
    response = client.get("/windsurf/tides/atlantis")

    assert response.status_code == 404
    assert_matches_schema(response.json(), "common/schemas/error.json")


def test_get_week_tides_upstream_failure_matches_error_contract(
    client, ukho, assert_matches_schema
):
    ukho.status_code = 500

    response = client.get("/windsurf/tides/chalkwell")

    assert response.status_code == 502
    assert_matches_schema(response.json(), "common/schemas/error.json")


def test_openapi_is_published(client):
    response = client.get("/windsurf/openapi.json")

    assert response.status_code == 200
    assert set(response.json()["paths"]) == {"/tides/{spot}"}
