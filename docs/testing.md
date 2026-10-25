# Testing

Every test lives in the root `tests/` folder, one subfolder per project, never next to the
code ([repository-structure.md](repository-structure.md)):

```
tests/
├── __init__.py                    ← in tests/ and EVERY folder below it (see below)
├── api/
│   ├── conftest.py                ← api fixtures: test env vars, token issuer, Postgres container
│   ├── unit/                      ← mirrors services/api/ (and scripts/api/seed/ under unit/seed/)
│   ├── integration/               ← mirrors services/api/
│   │   └── conftest.py            ← `session` (rolled back after each test), `saved_trip`
│   └── acceptance/                ← split by sub-app: the api's HTTP contracts
│       ├── conftest.py            ← `client`, `db`, `assert_matches_schema`
│       ├── common/schemas/        ← contracts shared by every sub-app (error shapes)
│       ├── trips/     test_trips_api.py     schemas/*.json
│       └── windsurf/  test_windsurf_api.py  schemas/*.json
└── trips-frontend/                ← see frontend.md#testing
```

```bash
make test                   # everything except e2e
make test-api               # the api: unit + integration + acceptance (needs Docker)
make test-api-unit          # fast, no Docker
make test-api-integration   # needs Docker
make test-api-acceptance    # needs Docker
make test-frontends         # every frontend's tests
uv run pytest tests/api/unit/trips/test_views.py -k redacts   # one file, from the repo root
```

There are no e2e tests yet. In the conventions, e2e tests are black-box: they run against
`docker compose up` and import no project code. `make e2e` will run them.

### `__init__.py` everywhere, default import mode

Every folder under `tests/`, including `tests/` itself, has an `__init__.py`. Each test module
then gets a unique dotted name (`tests.api.unit.trips.test_views`), so two files can share a
name (there are several `test_api.py`), and no test folder can shadow a real package (e.g.
`tests/api/` vs the `api` package). pytest runs in its default import mode; never switch to
`--import-mode=importlib`. `make lint` and CI fail if any test folder is missing its
`__init__.py`, so add one to every new folder.

## The api's test types

Integration and acceptance tests always run against a throwaway Postgres started by
[testcontainers](https://testcontainers-python.readthedocs.io/). It never touches the compose
database or your `.env`, and Docker is the only thing they need. The container is started
lazily, once per run, only if a test asks for a database fixture, so unit-only runs never start one.

| Type | What it tests | Database / network | Calls code via |
| --- | --- | --- | --- |
| **Unit** | One function or method's logic | None. Fakes for anything external (e.g. `httpx.MockTransport`) | Direct function calls |
| **Integration** | Code that talks to real infrastructure: queries, constraints, migrations | Real Postgres; each test's changes are rolled back | Direct function calls with a real `session` |
| **Acceptance** | The deployed app's HTTP behaviour and **contracts** | Real Postgres, data arranged by the test, tables emptied afterwards. External APIs are faked at the HTTP transport | `TestClient(api.main:app)`, using real URL paths (`/trips/...`) |

Acceptance is this repo's addition to the conventions' unit/integration/e2e: the tests are
in-process (they import the app), so they aren't e2e.

### Where a new test goes

- **Unit**: the function can run with no database. Put it at
  `tests/api/unit/<same path as the module>/test_<module>.py`. For example,
  `services/api/trips/views.py` → `tests/api/unit/trips/test_views.py`.
- **Integration**: it needs a real database. Use the same mirrored path under
  `tests/api/integration/`. Endpoint functions are plain functions, so test them by calling
  them with a `session`, not through HTTP.
- **Acceptance**: it's about what a client (the frontend or an agent) sees over HTTP. Put it
  in `tests/api/acceptance/<sub-app>/test_<sub-app>_api.py`.

## Naming

**Functions**: `test_<function_name>_<behaviour>`

```python
def test_build_trip_view_redacts_dates_for_non_owner(): ...
def test_decode_access_token_rejects_expired_token(): ...
```

**Methods**: group them in `Test<ClassName>`, then `test_<method_name>_<behaviour>`

```python
class TestTidesClient:
    def test_get_week_tides_raises_on_error_status(self): ...
```

SQLAlchemy models have no methods of their own, so their tests use the database operation
as the method name, e.g. `TestTripDay.test_insert_rejects_duplicate_day_number_in_a_trip`.

**Acceptance tests**: `test_<endpoint function>_<behaviour>`, where the behaviour usually says
which contract the response meets, e.g. `test_get_trip_as_owner_matches_owner_contract`.

## Acceptance tests are contract tests

Every response an API can return should be checked against a **hand-written JSON Schema**
(draft 2020-12) in `tests/api/acceptance/<sub-app>/schemas/`. These schemas are the contract that
the frontends and agents rely on. They're written by hand on purpose, not generated from
the Pydantic models: if a code change alters the API's shape, the test fails instead of the
contract quietly changing with it.

```python
def test_get_trip_as_owner_matches_owner_contract(
    client, auth_header, saved_trip, owner_id, assert_matches_schema
):
    response = client.get(f"/trips/{saved_trip.id}", headers=auth_header(owner_id))

    assert response.status_code == 200
    assert_matches_schema(response.json(), "trips/schemas/trip-owner.json")
```

Rules for schemas:

- **`additionalProperties: false` and every key in `required`** (including ones that can be
  `null`). A new or leaked field then breaks the contract. That matters most for security
  rules: `trip-public.json` requires dates and bookings to be `null`, so a leak of owner-only
  data fails the test with a message naming the exact field.
- **Use formats** (`uuid`, `date`, `email`). They're checked.
- **Cover error responses too.** `common/schemas/error.json` covers `{"detail": "..."}`
  errors, and `common/schemas/validation-error.json` covers 422s.
- **Reference other schemas by relative path**, e.g. `"$ref": "trip-owner.json"`, or
  `"../../common/schemas/error.json"` across folders. Paths are relative to
  `tests/api/acceptance/`.
- **Changing a schema means changing the API contract.** Do it only when the API change is
  intended, and check what the frontend or agents expect.

Contracts don't need to cover everything. Specific values that matter (e.g. that the right
trip came back) are asserted directly alongside the schema check.

### Arranging data

The `db` fixture is a session on the same database the app uses. Add rows and **commit** them,
because the app reads them over its own connections. Every table in every chain's schema is
truncated after each test.

### External services

Never call real external APIs, and **don't use the WireMock mocks in `docker/wiremock/` either**: they're
for the local compose stack. Every test arranges its own responses, so it can cover the
errors and edge cases it cares about.

- **Unit tests** give the client an `httpx.Client` backed by `httpx.MockTransport` returning
  the response the test needs (see `TestTidesClient`), or pass a fake client straight to the
  endpoint function.
- **Acceptance tests** override the sub-app's dependency, so that the real client runs over a
  fake transport. That way everything except the network is exercised:

```python
windsurf_app.dependency_overrides[get_tides_client] = lambda: TidesClient("test-key", fake_http)
```

Overrides go on the **sub-app** (`api.windsurf.api.app`), not on `main.app`. Each
mounted app resolves its own dependencies.

## Fixtures

| Fixture | Scope | From | Gives you |
| --- | --- | --- | --- |
| `make_token(sub, **claims)` | test | `tests/api/conftest.py` | a token the app accepts, signed like Clerk's; override or remove (`claim=None`) any claim to build an invalid one |
| `auth_header(user_id)` | test | `tests/api/conftest.py` | `{"Authorization": "Bearer <valid token>"}` |
| `user_id` | test | `tests/api/conftest.py` | a fresh Clerk-style user id (`user_…`) |
| `create_database()` | session | `tests/api/conftest.py` | context manager for an extra empty database (e.g. migration tests) |
| `database_url` | session | `tests/api/conftest.py` | the migrated test database |
| `session` | test | `tests/api/integration/conftest.py` | a session whose commits are rolled back |
| `client` | test | `tests/api/acceptance/conftest.py` | `TestClient` for the whole app |
| `db` | test | `tests/api/acceptance/conftest.py` | a session for arranging data; tables truncated afterwards |
| `assert_matches_schema(body, path)` | session | `tests/api/acceptance/conftest.py` | asserts a response body against a contract, listing every violation |

`tests/api/conftest.py` sets the `AUTH_*` settings, `ALLOWED_ORIGINS` and `UKHO_API_KEY` to fixed
test values before anything reads settings, so tests never depend on your `.env`.

### Tokens in tests

Tests act as their own token issuer, not Clerk or clerk-mock. `tests/api/conftest.py` creates
an RSA key pair for each run and serves its JWKS from a small HTTP server on a random local
port. `make_token` signs tokens with that key. The app then runs its **real** verification
(JWKS fetch, signature, issuer, expiry, `azp`) against tokens the tests control, with no
network access and no Clerk.
