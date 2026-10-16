# Backend structure and conventions

The backend is one uv project in `backend/`, using the standard **src layout**:

```
backend/
├── pyproject.toml           ← project metadata, dependencies, pytest + ruff config
├── uv.lock                  ← committed; `uv sync` installs exactly this
├── Dockerfile               ← one image for compose and Render
├── .env.example             ← copy to .env (`make init` does this)
├── src/houseplants/         ← the importable package
│   ├── main.py              ← mounts every sub-app; CORS; `/` and `/healthz`
│   ├── common/              ← settings, DB session, token verification, migration plumbing
│   ├── trips/               ← sub-app: trip itineraries
│   └── windsurf/            ← sub-app: tide windows
└── tests/                   ← see testing.md
```

`pyproject.toml` describes the project, so it lives at the project root next to `src/` and
`tests/`, not inside `src/`. Code under `src/` is only importable once it's installed
(`uv sync` installs it in editable mode), so tests and tools always import the package the
same way production does: `from houseplants.trips.api import app`.

## Dependencies

Use uv, never pip:

```bash
cd backend
uv add <package>          # runtime dependency
uv add --dev <package>    # test / tooling only
uv run <command>          # run anything inside the project's environment
```

Commit `pyproject.toml` and `uv.lock` together.

## Sub-apps

Each sub-app is a package with its own `FastAPI()` instance in `api.py`. Each one gets its
own `/docs`, `/openapi.json`, models and Alembic chain:

```
src/houseplants/trips/
├── api.py          ← `app = FastAPI(title="Trips API", ...)` and its routes
├── models.py       ← SQLAlchemy models, all in the `trips` Postgres schema
├── views.py        ← Pydantic response models + pure functions that build them
├── alembic.ini     ← this sub-app's migration chain (see migrations.md)
└── alembic/
```

Rules that keep each sub-app extractable into its own deployment later
(see [ARCHITECTURE.md](../ARCHITECTURE.md)):

- **Never import from another sub-app.** Only `houseplants.common` is shared.
- **Never query another sub-app's schema, or add a foreign key into it.** For example,
  `trips.trips.owner_id` is the token's `sub` claim (a Clerk user id), with nothing to reference.
- **`main.py` only mounts sub-apps.** Each sub-app must still run on its own, e.g.
  `uvicorn houseplants.trips.api:app`.

### Adding a sub-app

1. Create `src/houseplants/<name>/` with `__init__.py` and `api.py`
   (`app = FastAPI(title=..., version=...)`).
2. Add it to `SUB_APPS` in `src/houseplants/main.py`.
3. If it has tables, give it its own schema and migration chain (see
   [migrations.md](migrations.md)).
4. Optionally add demo data in `src/houseplants/<name>/seed.py`, and call it from
   `src/houseplants/seed.py` (see [local-development.md](local-development.md#seed-data)).
5. Add tests under `tests/unit/<name>/`, `tests/integration/<name>/` and
   `tests/acceptance/<name>/`, with JSON Schema contracts for every response (see
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
`houseplants.common.security`:

- **What's checked:**
  - an RS256 signature, against the issuer's JWKS (fetched once and cached)
  - `iss` must equal `AUTH_ISSUER`
  - `exp`/`nbf`, with 10 seconds of leeway
  - `azp` must be in `AUTH_AUTHORIZED_PARTIES` if the token has one.
- **The user id is the token's `sub`:** a Clerk id like `user_2ab…`. Store it as a plain
  string (e.g. `owner_id: Mapped[str]`), never as a UUID.
- **Dependencies for endpoints:**
  - `UserId`: the caller's user id; responds 401 if the token is missing or invalid.
  - `OptionalUserId`: the user id, or `None` for anonymous callers. Use it for endpoints
    that serve public and owner views.
- **Without `AUTH_ISSUER`,** every request is treated as anonymous, and a warning is logged.

| Setting | Locally (compose.env) | Production (Clerk) |
| --- | --- | --- |
| `AUTH_ISSUER` | `http://localhost:8082` (clerk-mock) | the instance's Frontend API URL, e.g. `https://clerk.yourdomain.com` |
| `AUTH_JWKS_URL` | `http://clerk-mock:8080/.well-known/jwks.json` | unset: defaults to `{AUTH_ISSUER}/.well-known/jwks.json` |
| `AUTH_AUTHORIZED_PARTIES` | `http://localhost:5173` | the frontends' URLs |

To try a real Clerk development instance locally, set those three in `backend/.env` (see
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
4. **Add a WireMock service to `docker-compose.yml`** with stubs in `mocks/<service>/`. Mock
   the external API's own request and response shape, so the real client code runs locally.
   Point `compose.env` at it (see [local-development.md](local-development.md)).

Tests don't use the WireMock mocks. Each test arranges its own responses, so it can cover
errors and edge cases (see [testing.md](testing.md)).

## Settings

All configuration is in `houseplants.common.settings.Settings` (pydantic-settings). It reads
environment variables first, then `backend/.env`. Add new settings there, with a default where
the app can run without one. Document each one in `.env.example`, and add it to `render.yaml`
if production needs it. Add a local default to `compose.env` if the compose stack needs a
different value from production.
