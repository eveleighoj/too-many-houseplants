# CLAUDE.md

A monorepo with one FastAPI backend, the **api** service (`services/api/`), which serves
several JSON APIs (`trips`, `windsurf`), each mounted as its own sub-app, plus Svelte
frontends as npm workspaces (`services/trips-frontend/` so far). The frontends and agents
are both just API clients. The layout follows the repository structure conventions
(docs/repository-structure.md).

Read the guide for the area you're changing before you change it:

| Guide | Read when |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | anything structural. Explains why it's built this way |
| [docs/repository-structure.md](docs/repository-structure.md) | adding or moving any file or folder: where things go, and this repo's deviations from the conventions |
| [docs/api.md](docs/api.md) | adding or changing api code, sub-apps, endpoints, auth, settings |
| [docs/contributing.md](docs/contributing.md) | committing, branching, rebasing, what CI checks |
| [docs/frontend.md](docs/frontend.md) | anything in a `services/*-frontend/` folder: structure, API client, generated types, tests, hosting |
| [docs/testing.md](docs/testing.md) | writing or changing any test |
| [docs/trips.md](docs/trips.md) | changing the trips data model: places, stops, stays, bookings, redaction |
| [docs/migrations.md](docs/migrations.md) | changing models or the database schema |
| [docs/local-development.md](docs/local-development.md) | running things locally, docker compose, mocked external APIs, seed data |

## Commands

Always run from the repo root (`make help` lists them all):

```bash
make setup              # install everything (.venv, node_modules, Chromium, commit hook)
make up                 # compose: api on :8000, trips frontend on :5173 (both live reload)
make seed               # reset local demo data (log in as the clerk-mock dev users)
make test               # all tests except e2e (api integration/acceptance need Docker)
make test-api-unit      # api unit tests: fast, no Docker
make test-frontends
make lint               # ruff, import-linter, prettier, eslint, svelte-check, tests/ __init__.py check
make format
make api-types          # regenerate frontend API types after an api change
make check-commits      # check your branch's commit messages, as CI does
make migration chain=trips m="..."   # autogenerate a migration
make migrate
```

For Python, use uv (`uv add`, `uv run`) from the root, never pip. For npm, use workspaces
from the root (`npm install <pkg> -w services/<frontend>`).

## Rules

- **Layout**: follow docs/repository-structure.md. Services in `services/`, every test in
  `tests/<project>/`, tooling in `scripts/`, shared Docker/Compose assets in `docker/`.
- **Imports**: api code is the `api` package (`from api.trips.models import Trip`).
- **Sub-app independence**: never import from another sub-app, query its schema or add
  foreign keys into it. Only `api.common` is shared. `make lint` enforces the imports
  (import-linter).
- **Migrations**: always generate them with Alembic autogenerate (`make migration`), never
  by hand. Then review the generated file.
- **Tests**:
  - They go in `tests/<project>/`, never next to the code. For the api:
    `tests/api/{unit,integration,acceptance}/`. Unit and integration tests mirror
    `services/api/`; acceptance tests are split by sub-app.
  - **Every folder under `tests/` needs an `__init__.py`** (pytest's default import mode;
    never `--import-mode=importlib`). CI fails otherwise.
  - Name tests `test_<function>_<behaviour>`, or for methods,
    `Test<Class>.test_<method>_<behaviour>`.
  - Every API response is checked against a hand-written JSON Schema in
    `tests/api/acceptance/<sub-app>/schemas/`. Changing a schema changes the API contract, so
    do it only when the API change is intended.
- **Auth**:
  - Users live in Clerk; the api only verifies tokens (RS256 via the issuer's JWKS, in
    `api.common.security`). User ids are Clerk ids, stored as plain strings.
  - Never add password or login handling to the api.
  - Locally the issuer is `clerk-mock` (`docker/wiremock/clerk/`). In tests, use the
    `make_token` / `auth_header` fixtures.
- **Databases in tests**: always testcontainers, never the dev database.
- **External APIs**: the base URL comes from settings, and the client takes an
  `httpx.Client`. Locally they're mocked by a WireMock service with stubs in
  `docker/wiremock/<service>/`. Tests never use those mocks; each test fakes its own responses.
- **Frontends**:
  - Each frontend is a static SvelteKit SPA and an npm workspace in `services/`.
  - Call the API only through `src/lib/api/client.ts` (`authFetch`).
  - Never hand-edit the generated `src/lib/api/*.d.ts`; run `make api-types` instead.
  - Its tests go in `tests/<frontend>/unit/` (components in `unit/components/`), named
    `*.test.ts`, importing the app by package name (`trips-frontend/src/lib/...`).
- **Commits and branches**:
  - Every commit message is a Conventional Commit (`feat(trips): …`, `fix: …`, `docs: …`).
  - Update branches with `git rebase origin/main`, never by merging `main` into them; PRs
    are rebase-merged.
  - Never edit `.gitignore` so it hides source files. Its Python template's `lib/` rule
    has hidden `services/*/src/lib/` twice; there's an exception for it.
- **Before finishing**: run `make lint` and `make test`. Run `make api-types-check` too if you
  changed the api.
