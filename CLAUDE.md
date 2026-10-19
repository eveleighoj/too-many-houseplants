# CLAUDE.md

A monorepo containing one FastAPI backend that serves several JSON APIs (`trips`,
`windsurf`), each mounted as its own sub-app, plus Svelte frontends in their own folders
(`trips-frontend/` so far).
The Svelte frontends and agents are both just API clients.

Read the guide for the area you're changing before you change it:

| Guide | Read when |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | anything structural. Explains why it's built this way |
| [docs/backend.md](docs/backend.md) | adding or changing backend code, sub-apps, endpoints, auth, settings |
| [docs/contributing.md](docs/contributing.md) | committing, branching, rebasing, what CI checks |
| [docs/frontend.md](docs/frontend.md) | anything in a `*-frontend/` folder: structure, API client, generated types, tests, hosting |
| [docs/testing.md](docs/testing.md) | writing or changing any backend test |
| [docs/trips.md](docs/trips.md) | changing the trips data model: places, stops, stays, bookings, redaction |
| [docs/migrations.md](docs/migrations.md) | changing models or the database schema |
| [docs/local-development.md](docs/local-development.md) | running things locally, docker compose, mocked external APIs, adding a frontend |

## Commands

Run from the repo root (`make help` lists them all):

```bash
make up                 # compose: API on :8000, trips frontend on :5173 (both live reload)
make seed               # reset local demo data (log in as the clerk-mock dev users)
make test               # all tests, backend + frontend (backend integration/acceptance need Docker)
make test-unit          # backend unit tests: fast, no Docker
make test-trips-frontend
make lint               # ruff + prettier/eslint/svelte-check
make api-types          # regenerate frontend API types after a backend API change
make check-commits      # check your branch's commit messages, as CI does
make format
make migration chain=trips m="..."   # autogenerate a migration
make migrate
```

For Python, use uv (`uv add`, `uv run`), never pip. Backend commands run from `backend/`.
Frontend commands (npm) run from their `*-frontend/` folder.

## Rules

- **Package layout**: backend code lives in `backend/src/houseplants/`. Import it as
  `houseplants.<sub-app>....`.
- **Sub-app independence**: never import from another sub-app, query its schema or add
  foreign keys into it. Only `houseplants.common` is shared.
- **Migrations**: always generate them with Alembic autogenerate (`make migration`), never
  by hand. Then review the generated file.
- **Tests**: they go in `backend/tests/{unit,integration,acceptance}/`, never next to the
  code. Unit and integration tests mirror `src/houseplants/`; acceptance tests are split by
  API.
  - Name tests `test_<function>_<behaviour>`, or for methods,
    `Test<Class>.test_<method>_<behaviour>`.
  - Every API response is checked against a hand-written JSON Schema in
    `tests/acceptance/<api>/schemas/`. Changing a schema changes the API contract, so do it
    only when the API change is intended.
- **Auth**:
  - Users live in Clerk; the backend only verifies tokens (RS256 via the issuer's JWKS, in
    `houseplants.common.security`). User ids are Clerk ids, stored as plain strings.
  - Never add password or login handling to the backend.
  - Locally the issuer is `clerk-mock` (`mocks/clerk/`). In tests, use the `make_token` /
    `auth_header` fixtures.
- **Databases in tests**: always testcontainers, never the dev database.
- **External APIs**: the base URL comes from settings, and the client takes an
  `httpx.Client`. Locally they're mocked by a WireMock service with stubs in
  `mocks/<service>/`. Tests never use those mocks; each test fakes its own responses.
- **Frontends**:
  - Each frontend is a static SvelteKit SPA in its own folder.
  - Call the API only through `src/lib/api/client.ts` (`authFetch`).
  - Never hand-edit the generated `src/lib/api/*.d.ts`; run `make api-types` instead.
  - Its tests go in `<frontend>/tests/{unit,component}/`.
- **Commits and branches**:
  - Every commit message is a Conventional Commit (`feat(trips): …`, `fix: …`, `docs: …`).
  - Update branches with `git rebase origin/main`, never by merging `main` into them; PRs
    are rebase-merged.
  - Never edit `.gitignore` so it hides source files. Its Python template's `lib/` rule
    once hid `trips-frontend/src/lib/`.
- **Before finishing**: run `make lint` and `make test`. Run `make api-types-check` too if you
  changed the backend API.
