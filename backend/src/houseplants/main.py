"""The single deployed backend: mounts every sub-app, and configures CORS once for all of them.

Nothing else belongs here — each sub-app must stay runnable on its own (e.g.
`uvicorn houseplants.trips.api:app`) so it can be split out into its own deployment later.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from houseplants.common.settings import get_settings
from houseplants.trips.api import app as trips_app
from houseplants.windsurf.api import app as windsurf_app

SUB_APPS = {
    "trips": trips_app,
    "windsurf": windsurf_app,
}

app = FastAPI(title="too-many-houseplants", docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
    # Tokens travel in the Authorization header, not cookies.
    allow_credentials=False,
)

for prefix, sub_app in SUB_APPS.items():
    app.mount(f"/{prefix}", sub_app)


@app.get("/")
def index() -> dict:
    """Machine-readable directory of the APIs this deployment hosts."""
    return {
        "apis": [
            {"name": sub_app.title, "docs": f"/{prefix}/docs", "openapi": f"/{prefix}/openapi.json"}
            for prefix, sub_app in SUB_APPS.items()
        ]
    }


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict:
    return {"status": "ok"}
