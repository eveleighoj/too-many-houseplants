from collections.abc import Iterator
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, HTTPException, status

from houseplants.common.docs import SWAGGER_UI_PARAMETERS
from houseplants.common.settings import get_settings
from houseplants.windsurf.models import KNOWN_SPOTS, SpotTides
from houseplants.windsurf.tides import TidesClient

app = FastAPI(title="Windsurf API", version="1.0.0", swagger_ui_parameters=SWAGGER_UI_PARAMETERS)


def get_tides_client() -> Iterator[TidesClient]:
    settings = get_settings()
    if not settings.ukho_api_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="UKHO_API_KEY is not set")
    with httpx.Client(base_url=settings.ukho_base_url, timeout=10) as http:
        yield TidesClient(settings.ukho_api_key, http)


@app.get(
    "/tides/{spot}",
    summary="Get tide windows for the next 7 days for a windsurfing spot",
    tags=["Tides"],
)
def get_week_tides(
    spot: str, client: Annotated[TidesClient, Depends(get_tides_client)]
) -> SpotTides:
    known = KNOWN_SPOTS.get(spot)
    if known is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"unknown spot: {spot}")

    try:
        days = client.get_week_tides(known.station_id, known.hours_before, known.hours_after)
    except httpx.HTTPError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="failed to fetch tides") from error

    return SpotTides(spot=spot, days=days)
