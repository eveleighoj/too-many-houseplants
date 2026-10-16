# Local development

Needs [uv](https://docs.astral.sh/uv/) and Docker.

```bash
make init                               # uv sync, npm ci, and create backend/.env
make up                                 # db → migrate → api, on http://localhost:8000
make seed                               # demo trips (re-run any time to reset them)
```

`make help` lists every target.

## The compose stack

`docker-compose.yml` at the repo root runs the whole stack:

| Service | What it does |
| --- | --- |
| `db` | Postgres 16 on `localhost:5432` (user/password/db: `houseplant`) |
| `migrate` | one-shot. Runs every Alembic chain, then exits. `api` waits for it to succeed |
| `api` | the FastAPI app from `backend/Dockerfile`. `backend/src` is mounted, so code changes reload automatically |
| `trips-frontend` | the trips Svelte app's Vite dev server on http://localhost:5173, with hot reload (see [frontend.md](frontend.md)) |
| `clerk-mock` | WireMock standing in for Clerk, on `localhost:8082`. Serves the JWKS the API verifies tokens against, and ready-made tokens for the dev users (see [mocks/clerk/](../mocks/clerk/README.md)) |
| `ukho-mock` | WireMock standing in for the UKHO tidal API, on `localhost:8081`. Serves a week of tides starting today (see [mocks/ukho/](../mocks/ukho/README.md)) |

Rebuild (`make up` does this) after changing dependencies, because they're baked into the
image. Code changes only need the reload.

The backend containers load two env files, and the later one wins:

1. `compose.env` (committed) holds the local defaults, e.g. pointing UKHO at `ukho-mock`.
2. `backend/.env` (yours, gitignored) holds your own settings and overrides those defaults.

`DATABASE_URL` is always forced to the `db` service, because `backend/.env` points it at
`localhost` for running on the host.

## External APIs are mocked by default

Every external API the backend calls gets a WireMock service in compose, with stubs and
seeded data in `mocks/<service>/`. The stack then works with no keys and gives the same data
every time. Production code doesn't know about the mocks: only the base URL setting changes.

To use the **real** UKHO API instead, uncomment and fill in these lines in `backend/.env`,
then run `make up`:

```bash
UKHO_BASE_URL=https://admiraltyapi.azure-api.net/uktidalapi/api/V1
UKHO_API_KEY=your-key
```

Leave lines you aren't using **commented out**. A blank `UKHO_API_KEY=` would still override
the mock's key, and `/windsurf` would return 503.

To change the mock data, edit `mocks/ukho/`, then run `docker compose restart ukho-mock`. You
can see the loaded stubs at http://localhost:8081/__admin/mappings.

## Running the backend on the host instead

Useful for a debugger:

```bash
make db-up      # only Postgres
make migrate
make dev        # uvicorn --reload on :8000, using backend/.env
```

Don't run this and `make up` at the same time, because both use port 8000.

On the host, `compose.env` isn't loaded, so `/windsurf` returns 503 unless `backend/.env` sets
a UKHO key. To use the mock from the host, run `docker compose up -d ukho-mock` and set
`UKHO_BASE_URL=http://localhost:8081` plus any `UKHO_API_KEY`.

## Seed data

`make seed` resets the local database's demo data. It's safe to re-run: the demo trips and
their places are replaced, and nothing else in the database is touched. Users aren't in the
database at all (they live in Clerk), so the trips belong to clerk-mock's dev users.

**Every seeded row has the same id on every run**, so you can bookmark URLs, keep curl
commands and recognise rows in pgAdmin. Ids are readable: the first block is the kind of
row, and the last block is its number.

| Dev user (log in on the frontend's login page) | Owns |
| --- | --- |
| **Demo** (`user_demo`) | Scottish Highlands (4 days, 3 stays, bookings for a stay, a stop and a ferry), Lake District (2 days), Japan (no days yet) |
| **Friend** (`user_friend`) | Cornwall surf trip |

To own the demo trips with your own **real** Clerk account instead, set
`SEED_DEMO_USER_ID=<your Clerk user id>` in `backend/.env` and re-seed.

| Kind (first block) | Numbering (last block) | Example |
| --- | --- | --- |
| `00000002` trip | N | trip 1 = `00000002-0000-4000-8000-000000000001` |
| `00000003` place | trip × 100 + N | trip 1's 3rd place = `00000003-0000-4000-8000-000000000103` |
| `00000004` day | trip × 100 + day | trip 1, day 2 = `00000004-0000-4000-8000-000000000102` |
| `00000005` stop | trip × 10000 + day × 100 + stop | trip 1, day 2, stop 3 = `00000005-0000-4000-8000-000000010203` |
| `00000006` stay | trip × 100 + N | |
| `00000007` booking | trip × 100 + N | |

| Trip | Id | Owner |
| --- | --- | --- |
| 1. Scottish Highlands road trip | `00000002-0000-4000-8000-000000000001` | demo |
| 2. Lake District weekend | `00000002-0000-4000-8000-000000000002` | demo |
| 3. Japan (still planning) | `00000002-0000-4000-8000-000000000003` | demo |
| 4. Cornwall surf trip | `00000002-0000-4000-8000-000000000004` | friend |

For example, http://localhost:5173/trips/00000002-0000-4000-8000-000000000001, or
`curl localhost:8000/trips/00000002-0000-4000-8000-000000000004`. A new sub-app's seed picks
the next free kind (`houseplants.common.seeding.seed_id`).

Log in as Demo and open the Cornwall trip to see the **redacted** view (no dates, stays or
bookings). Log in as Friend to see it in full. Trip dates are relative to the day you seed,
so they always look upcoming. Seed places have no Google/Apple ids, so their map links are
`null`.

Each sub-app keeps its own seed data in `src/houseplants/<sub-app>/seed.py`.
`src/houseplants/seed.py` runs them all, and refuses to run against a non-local database.
Want a new sub-app's data in the seed? Add its `seed.py` and call it from there.

## Trying the API

Every sub-app has interactive docs, where you can call any endpoint: `/trips/docs` and
`/windsurf/docs`. `/` lists them. To call endpoints that need a login:

1. Open **http://localhost:8082** (clerk-mock) and click **Copy token** next to a dev user.
2. On the docs page, click **Authorize**, paste the token, and click **Authorize** again.
   Paste just the token: Swagger adds `Bearer` itself.

Swagger remembers the token across reloads, and the dev tokens last until 2100, so you only
do this once per browser. Log out in Swagger's **Authorize** dialog to switch user. The
trips docs link to the token page locally.

From the command line:

```bash
TOKEN=$(curl -s localhost:8082/dev/users | jq -r '.users[] | select(.id=="user_demo") | .token')
curl -s localhost:8000/trips/ -H "Authorization: Bearer $TOKEN"
```

## Frontends

Each frontend runs as its own compose service. `trips-frontend` is on
http://localhost:5173; after `make seed`, log in by picking the Demo or Friend dev user. See
[frontend.md](frontend.md) for running a frontend on the host instead, and for adding
another one.
