# The api service

The backend is one Python project, the **api** service. The root `pyproject.toml` is the
project; its import package is `services/api/` (`import api`). See
[repository-structure.md](repository-structure.md) for how that fits the repo's conventions.

```
services/api/
├── main.py              ← mounts every sub-app; CORS; `/` and `/healthz`
├── common/              ← settings, DB session, token verification, migration plumbing
├── trips/               ← sub-app: trip itineraries (see trips.md)
├── windsurf/            ← sub-app: tide windows
└── Dockerfile           ← base / test / runtime stages, built from the repo root
```

uv installs the project in editable mode into the root `.venv`, so `from api.trips.api import app`
works from anywhere in the repo, the same way it does in the production image (where it's
installed normally, without the source).

## Dependencies

Use uv, never pip, from the repo root:

```bash
uv add <package>          # runtime dependency (written to pyproject.toml)
uv add --dev <package>    # test / tooling only
uv run <command>          # run anything inside the .venv
```

Commit `pyproject.toml` and `uv.lock` together. (This repo uses `uv.lock` instead of the
conventions' `requirements/` files; see [repository-structure.md](repository-structure.md).)

## Sub-apps

Each sub-app is a package with its own `FastAPI()` instance in `api.py`. Each one gets its
own `/docs`, `/openapi.json`, models and Alembic chain:

```
services/api/trips/
├── api.py          ← `app = FastAPI(title="Trips API", ...)` and its routes
├── models.py       ← SQLAlchemy models, all in the `trips` Postgres schema
├── views.py        ← Pydantic response models + pure functions that build them
├── alembic.ini     ← this sub-app's migration chain (see migrations.md)
└── migrations/
```

Rules that keep each sub-app extractable into its own deployment later
(see [ARCHITECTURE.md](../ARCHITECTURE.md)):

- **Never import from another sub-app.** Only `api.common` is shared. `make lint` enforces
  this with import-linter (the contracts are in `pyproject.toml`).
- **Never query another sub-app's schema, or add a foreign key into it.** For example,
  `trips.trips.owner_id` is the token's `sub` claim (a Clerk user id), with nothing to reference.
- **`main.py` only mounts sub-apps.** Each sub-app must still run on its own, e.g.
  `uvicorn api.trips.api:app`.

### Adding a sub-app

1. Create `services/api/<name>/` with `__init__.py` and `api.py`
   (`app = FastAPI(title=..., version=...)`).
2. Add it to `SUB_APPS` in `services/api/main.py`, and to the import-linter `independence`
   contract in `pyproject.toml`.
3. If it has tables, give it its own schema and migration chain (see
   [migrations.md](migrations.md)).
4. Optionally add demo data in `scripts/api/seed/<name>.py`, and call it from
   `scripts/api/seed/__init__.py` (see [local-development.md](local-development.md#seed-data)).
5. Add tests under `tests/api/unit/<name>/`, `tests/api/integration/<name>/` and
   `tests/api/acceptance/<name>/`, with JSON Schema contracts for every response (see
   [testing.md](testing.md)).

### Writing endpoints

- **Write route handlers as plain functions with typed dependencies** (`DbSession`, `UserId`,
  `OptionalUserId`). Unit and integration tests can then call them directly, without HTTP.
- **Return Pydantic models.** Response JSON uses camelCase (`dayNumber`), via the `View`
  base model's alias generator.
- **Raise `HTTPException` for errors**, so every error body is `{"detail": "..."}`.
- **Keep shaping logic in pure functions** (like `trips/views.py`), so it can be unit tested
  without a database.

## Auth

Users live in [Clerk](https://clerk.com) (see [ARCHITECTURE.md](../ARCHITECTURE.md#auth)). The
backend never handles passwords or logins: it only **verifies** bearer tokens, in
`api.common.security`:

- **What's checked:**
  - an RS256 signature, against the issuer's JWKS (fetched once and cached)
  - `iss` must equal `AUTH_ISSUER`
  - `exp`/`nbf`, with 10 seconds of leeway
  - `azp` must be in `AUTH_AUTHORIZED_PARTIES` if the token has one.
- **The user id is the token's `sub`:** a Clerk id like `user_2ab…`. Store it as a plain
  string (e.g. `owner_id: Mapped[str]`), never as a UUID.
- **Dependencies for endpoints:**
  - `UserId`: the caller's user id; responds 401 if the token is missing or invalid.
  - `OptionalUserId`: the user id, or `None` for anonymous callers, for an endpoint that
    should also work signed out. No trips endpoint uses it: trips need sign-in.
- **Without `AUTH_ISSUER`,** every request is treated as anonymous, and a warning is logged.

| Setting | Locally (docker/compose.env) | Production (Clerk) |
| --- | --- | --- |
| `AUTH_ISSUER` | `http://localhost:8082` (clerk-mock) | the instance's Frontend API URL, e.g. `https://clerk.yourdomain.com` |
| `AUTH_JWKS_URL` | `http://clerk-mock:8080/.well-known/jwks.json` | unset: defaults to `{AUTH_ISSUER}/.well-known/jwks.json` |
| `AUTH_AUTHORIZED_PARTIES` | `http://localhost:5173` | the frontends' URLs |

To try a real Clerk development instance locally, set those three in `.env` (see
`.env.example`).

## Calling external APIs

Follow the pattern in `windsurf` (UKHO tidal API) for every external service:

1. **Make the base URL and the key settings**, e.g. `ukho_base_url` (defaulting to the real
   URL) and `ukho_api_key`. Never hardcode the URL in the client.
2. **Have the client take an `httpx.Client`** instead of building its own. Create it in a
   FastAPI dependency (e.g. `get_tides_client`) from settings, closed after the request. Tests
   can then pass a client backed by `httpx.MockTransport`, or override the dependency.
3. **If the key is missing, return a 503 from the dependency.** Don't crash at startup, and
   never fall back to fake data in application code.
4. **Add a WireMock service to `docker-compose.yml`** with stubs in `docker/wiremock/<service>/`. Mock
   the external API's own request and response shape, so the real client code runs locally.
   Point `docker/compose.env` at it (see [local-development.md](local-development.md)).

Tests don't use the WireMock mocks. Each test arranges its own responses, so it can cover
errors and edge cases (see [testing.md](testing.md)).

## Settings

All configuration is in `api.common.settings.Settings` (pydantic-settings). It reads
environment variables first, then the root `.env`. Add new settings there, with a default where
the app can run without one. Document each one in the root `.env.example`, and add it to `render.yaml`
if production needs it. Add a local default to `docker/compose.env` if the compose stack needs a
different value from production.
