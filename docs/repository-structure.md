# Repository structure

This repo follows the
[Repository Structure Conventions](https://gist.github.com/eveleighoj/580410fbfdbac670c8274ffde0049d23).
Read those for the rules and the reasoning behind them. This page shows how they apply here,
and lists the few places this repo deliberately differs.

## Which layout

One Python project (the `api` service) and one or more Node projects (one per frontend). That
is the convention's **Example 5b** (a Python JSON API plus a separate frontend app), with the
Node side already set up as **npm workspaces** (Example 6's shape), so adding
`windsurf-frontend` is just another workspace.

```
repo/
├── services/
│   ├── api/                      ← the api's Python import package (`import api`)
│   │   ├── main.py               ← mounts every sub-app
│   │   ├── common/               ← shared: settings, DB, auth, migration plumbing
│   │   ├── trips/                ← sub-app: models, views, routes, alembic.ini, migrations/
│   │   ├── windsurf/             ← sub-app
│   │   └── Dockerfile            ← base / test / runtime stages; built from the repo root
│   └── trips-frontend/           ← SvelteKit SPA (an npm workspace)
│       ├── package.json
│       ├── vite.config.ts, vitest.unit.config.ts, vitest.components.config.ts
│       ├── src/
│       └── Dockerfile            ← static build served by nginx
├── tests/                        ← every test, one folder per project
│   ├── __init__.py               ← and in every folder below
│   ├── api/{unit,integration,acceptance}/
│   └── trips-frontend/unit/      ← unit/components/ runs in a headless browser
├── scripts/                      ← tooling, never copied into images
│   ├── api/seed/                 ← `make seed` (python -m scripts.api.seed)
│   ├── api/export_openapi.py
│   ├── trips-frontend/generate-api-types.js
│   ├── generate-clerk-mock-tokens.py
│   └── check-commits.sh
├── docker/                       ← shared Docker/Compose assets
│   ├── compose.env               ← local defaults for the api containers
│   ├── nginx-spa.conf            ← SPA fallback for frontend images
│   └── wiremock/{clerk,ukho}/    ← mocks of external services (compose)
├── docs/
├── pyproject.toml                ← the api project + all Python tool config
├── uv.lock
├── package.json                  ← npm workspaces glue + Node tool config/devDependencies
├── package-lock.json
├── vitest.config.ts              ← runs every frontend's test projects
├── eslint.config.js, prettier.config.js
├── docker-compose.yml
├── render.yaml
└── Makefile
```

One `.venv` (uv) and one `node_modules` (npm) at the root. Run everything from the root: `make help`.

## Where new things go

| Adding… | Goes in |
| --- | --- |
| an api sub-app (e.g. `plants`) | `services/api/plants/`, tests in `tests/api/{unit,integration,acceptance}/plants/`, an import-linter `independence` entry in `pyproject.toml` |
| a Python dependency | `uv add <pkg>` (or `uv add --dev <pkg>` for tooling) — writes `pyproject.toml` and `uv.lock` |
| a frontend (e.g. `windsurf-frontend`) | `services/windsurf-frontend/` as a new workspace in the root `package.json`, tests in `tests/windsurf-frontend/`, its own `Dockerfile` and `vitest.*.config.ts` (see [frontend.md](frontend.md)) |
| a frontend dependency | `npm install <pkg> -w services/<frontend>` |
| a test | `tests/<project>/<type>/` mirroring the source's packages and modules, with an `__init__.py` in every new folder ([testing.md](testing.md)) |
| a dev/maintenance script | `scripts/` (or `scripts/<project>/` if it's for one project) |
| a migration | generated into `services/api/<sub-app>/migrations/versions/` ([migrations.md](migrations.md)) |
| a mock of an external API | `docker/wiremock/<service>/`, plus a compose service ([local-development.md](local-development.md)) |
| a shared Docker asset | `docker/` (each Dockerfile stays next to its service) |

## Deliberate deviations from the conventions

| Convention | This repo | Why |
| --- | --- | --- |
| `requirements/*.in` → hashed `*.txt` via `pip-compile` | **`uv.lock`**, managed with `uv add` / `uv lock` / `uv sync` | Chosen for uv's speed and single lockfile. `make lock` runs `uv lock`; Docker installs with `uv sync --locked`. |
| Test types `unit`, `integration`, `e2e` | **`acceptance`** as well, for the api | The api's JSON-Schema contract tests run in-process (FastAPI `TestClient`, data arranged through the ORM), so they aren't black-box e2e. True e2e tests are still to come. |
| Docker `test` stage runs all of the project's tests | it runs **unit tests only** | Integration and acceptance tests need Postgres via testcontainers, i.e. a Docker daemon the build doesn't have. CI runs them outside the image against the same lockfile. |
| Every service is deployed from its Dockerfile | frontends deploy as **Render static sites** | Free hosting. Their Dockerfiles (nginx) are for running the built site locally and for future e2e tests. |
| Migrations: one `migrations/` per database | **one chain per api sub-app**, each in its own Postgres schema (`services/api/<sub-app>/migrations/`) | So a sub-app can be split out with its tables and history (see [ARCHITECTURE.md](../ARCHITECTURE.md)). They still share the convention's advisory lock and run only from the api. |
| Node tests in `tests/<project>/{unit,integration}/` named `*.test.ts` | same, plus `unit/components/` runs in a headless browser | Vitest browser mode needs a separate project; the folder decides which. |
| Dependency updates via Renovate | not set up yet | To do: `renovate.json` with the uv, npm, Docker and GitHub Actions managers. |
