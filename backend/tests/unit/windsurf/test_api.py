import httpx
import pytest
from fastapi import HTTPException

from houseplants.common.settings import get_settings
from houseplants.windsurf.api import get_tides_client, get_week_tides
from houseplants.windsurf.models import TideDay
from houseplants.windsurf.tides import TidesClient


class FakeTidesClient:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls: list[tuple[str, int, int]] = []

    def get_week_tides(self, station_id: str, hours_before: int, hours_after: int):
        self.calls.append((station_id, hours_before, hours_after))
        if self.error:
            raise self.error
        return [TideDay(date="2026-06-01", sunrise="06:00", sunset="21:00")]


# get_tides_client only builds the client; no request is ever made in these tests.


def test_get_tides_client_uses_configured_api_key():
    client = next(get_tides_client())

    assert isinstance(client, TidesClient)
    assert client.api_key == get_settings().ukho_api_key


def test_get_tides_client_uses_configured_base_url(monkeypatch):
    monkeypatch.setattr(get_settings(), "ukho_base_url", "https://ukho.test/api")

    client = next(get_tides_client())

    assert client.http.base_url == "https://ukho.test/api/"


def test_get_tides_client_closes_http_client_after_use():
    dependency = get_tides_client()
    client = next(dependency)

    dependency.close()

    assert client.http.is_closed


@pytest.mark.parametrize("api_key", [None, ""])
def test_get_tides_client_raises_503_without_api_key(monkeypatch, api_key):
    monkeypatch.setattr(get_settings(), "ukho_api_key", api_key)

    with pytest.raises(HTTPException) as error:
        next(get_tides_client())

    assert error.value.status_code == 503


def test_get_week_tides_uses_the_spots_station_and_hours():
    client = FakeTidesClient()

    result = get_week_tides("uncle-toms", client)

    assert client.calls == [("0110", 2, 4)]
    assert result.spot == "uncle-toms"
    assert result.days[0].date == "2026-06-01"


def test_get_week_tides_raises_404_for_unknown_spot():
    with pytest.raises(HTTPException) as error:
        get_week_tides("atlantis", FakeTidesClient())

    assert error.value.status_code == 404


def test_get_week_tides_raises_502_when_upstream_fails():
    with pytest.raises(HTTPException) as error:
        get_week_tides("chalkwell", FakeTidesClient(error=httpx.ConnectError("boom")))

    assert error.value.status_code == 502
