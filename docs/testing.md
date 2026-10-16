# Testing the backend

Frontend tests are covered in [frontend.md](frontend.md#testing).

All backend tests live in `backend/tests/`, never alongside the code, and are run with
pytest via uv:

```bash
make test              # everything
make test-unit         # fast, no Docker
make test-integration  # needs Docker
make test-acceptance   # needs Docker
# or directly, from backend/:
uv run pytest tests/unit/trips/test_views.py -k redacts
```

Integration and acceptance tests always run against a throwaway Postgres started by
[testcontainers](https://testcontainers-python.readthedocs.io/). It never touches the compose
database or your `.env`, and Docker is the only thing they need. The container is started
lazily, once per run, only if a test asks for a database fixture, so unit-only runs never start one.

## The three test types

```
backend/tests/
├── conftest.py            ← shared: test env vars, token issuer, Postgres container, migrated database
├── unit/                  ← mirrors src/houseplants/
│   ├── common/test_security.py
│   ├── trips/test_views.py
│   └── windsurf/test_tides.py
├── integration/           ← mirrors src/houseplants/
│   ├── conftest.py        ← `session` fixture (rolled back after each test)
│   ├── common/test_migrations.py
│   └── trips/test_api.py
└── acceptance/            ← split by API, not by module
    ├── conftest.py        ← `client`, `db`, `assert_matches_schema`
    ├── common/schemas/    ← contracts shared by every API (error shapes)
    ├── trips/     test_trips_api.py     schemas/*.json
    └── windsurf/  test_windsurf_api.py  schemas/*.json
```

| Type | What it tests | Database / network | Calls code via |
| --- | --- | --- | --- |
| **Unit** | One function or method's logic | None. Fakes for anything external (e.g. `httpx.MockTransport`) | Direct function calls |
| **Integration** | Code that talks to real infrastructure: queries, constraints, migrations | Real Postgres; each test's changes are rolled back | Direct function calls with a real `session` |
| **Acceptance** | The deployed app's HTTP behaviour and **contracts** | Real Postgres, data arranged by the test, tables emptied afterwards. External APIs are faked at the HTTP transport | `TestClient(houseplants.main:app)`, using real URL paths (`/trips/...`) |

### Where a new test goes

- **Unit**: the function can run with no database. Put it at
  `tests/unit/<same path as the module>/test_<module>.py`. For example,
  `src/houseplants/trips/views.py` → `tests/unit/trips/test_views.py`.
- **Integration**: it needs a real database. Use the same mirrored path under
  `tests/integration/`. Endpoint functions are plain functions, so test them by calling them
  with a `session`, not through HTTP.
- **Acceptance**: it's about what a client (the frontend or an agent) sees over HTTP. Put it
  in `tests/acceptance/<api>/test_<api>_api.py`.

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
(draft 2020-12) in `tests/acceptance/<api>/schemas/`. These schemas are the contract that
the frontends and agents rely on. They're written by hand on purpose, not generated from
the Pydantic models: if a code change alters the API's shape, the test fails instead of the
contract quietly changing with it.

```python
def test_get_trip_as_owner_matches_owner_contract(client, auth_header, saved_trip, owner_id, assert_matches_schema):
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
  `tests/acceptance/`.
- **Changing a schema means changing the API contract.** Do it only when the API change is
  intended, and check what the frontend or agents expect.

Contracts don't need to cover everything. Specific values that matter (e.g. that the right
trip came back) are asserted directly alongside the schema check.

### Arranging data

The `db` fixture is a session on the same database the app uses. Add rows and **commit** them,
because the app reads them over its own connections. Every table in every chain's schema is
truncated after each test.

### External services

Never call real external APIs, and **don't use the WireMock mocks in `mocks/` either**: they're
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

Overrides go on the **sub-app** (`houseplants.windsurf.api.app`), not on `main.app`. Each
mounted app resolves its own dependencies.

## Fixtures

| Fixture | Scope | From | Gives you |
| --- | --- | --- | --- |
| `make_token(sub, **claims)` | test | `tests/conftest.py` | a token the app accepts, signed like Clerk's; override or remove (`claim=None`) any claim to build an invalid one |
| `auth_header(user_id)` | test | `tests/conftest.py` | `{"Authorization": "Bearer <valid token>"}` |
| `user_id` | test | `tests/conftest.py` | a fresh Clerk-style user id (`user_…`) |
| `create_database()` | session | `tests/conftest.py` | context manager for an extra empty database (e.g. migration tests) |
| `database_url` | session | `tests/conftest.py` | the migrated test database |
| `session` | test | `tests/integration/conftest.py` | a session whose commits are rolled back |
| `client` | test | `tests/acceptance/conftest.py` | `TestClient` for the whole app |
| `db` | test | `tests/acceptance/conftest.py` | a session for arranging data; tables truncated afterwards |
| `assert_matches_schema(body, path)` | session | `tests/acceptance/conftest.py` | asserts a response body against a contract, listing every violation |

`tests/conftest.py` sets the `AUTH_*` settings, `ALLOWED_ORIGINS` and `UKHO_API_KEY` to fixed
test values before anything reads settings, so tests never depend on your `.env`.

### Tokens in tests

Tests act as their own token issuer, not Clerk or clerk-mock. `tests/conftest.py` creates
an RSA key pair for each run and serves its JWKS from a small HTTP server on a random local
port. `make_token` signs tokens with that key. The app then runs its **real** verification
(JWKS fetch, signature, issuer, expiry, `azp`) against tokens the tests control, with no
network access and no Clerk.
