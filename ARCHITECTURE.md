# Project Architecture Summary

This document summarizes the architecture decisions made for this project, to bring context into a fresh session (e.g. Claude Code) working against the repository.

## Core Stack

- **Backend**: FastAPI (Python) — pure JSON API, no server-rendered HTML
- **Frontend**: Svelte (static SPA, built with Vite) — not SvelteKit SSR, for now
- **Database migrations**: Alembic
- **Hosting**: Render
- **Auth**: [Clerk](https://clerk.com) — the API verifies Clerk-issued JWTs
- **Python tooling**: uv (dependencies, virtualenv, running commands)
- **Testing**: pytest

## Why this split (not Jinja2, not a Svelte-only app)

- The API must be usable directly by **authenticated agents**, not just the human frontend — this requires a clean, structured JSON API regardless of what the frontend looks like. This settled the architecture: FastAPI can't just render HTML (Jinja2) because that doesn't serve the agent use case well.
- A Svelte-only app (no Python backend) was ruled out because Alembic/SQLAlchemy/Python expertise is already in use and there's no benefit to rewriting the data layer in JS.
- Conclusion: FastAPI's only job is JSON in/out. The Svelte frontend and any agents are both just **clients** of the same API, with no special-casing between them.

## One FastAPI app hosting multiple APIs (for now)

The backend is **one single FastAPI app/deployment**, not separate FastAPI services per sub-project. Inside that one app, each sub-project (`trips`, `windsurf`, etc.) is its own **mounted sub-application**, each with its own routes, models, and own OpenAPI docs page — but all running in the same process, same container, same deploy.

```python
# services/api/main.py
from fastapi import FastAPI
from api.trips.api import app as trips_app
from api.windsurf.api import app as windsurf_app

app = FastAPI()
app.mount("/trips", trips_app)  # docs at /trips/docs
app.mount("/windsurf", windsurf_app)  # docs at /windsurf/docs
```

Each sub-app (`services/api/trips/api.py`, `services/api/windsurf/api.py`) is its own `FastAPI()` instance with its own routers and its own `/docs` — genuinely separate API surfaces, just **not separately deployed**. This gives clean separation of concerns in code without the operational overhead (and cost) of running multiple containers right now.

**Planned evolution, explicitly not done yet**: each sub-app is written so it could later be lifted out into its own standalone FastAPI deployment (its own container, own Render service) with minimal change — i.e. avoid tightly coupling sub-apps to each other or to the parent `main.py` beyond the mount point, so a future split to microservices is mechanical rather than a rewrite.

Each frontend (if one exists for a given sub-project) is still its own Svelte app, built and deployed independently — **one frontend folder per frontend to host**, not one shared frontend covering everything. (The backend consolidation above doesn't apply to frontends — those remain separate per sub-project since they're free to host and benefit from independent deploys.)

### Repo structure (monorepo, one backend deployment, multiple frontend deployments)

The repo follows the [Repository Structure Conventions](https://gist.github.com/eveleighoj/580410fbfdbac670c8274ffde0049d23)
(one Python project, Node frontends as npm workspaces). [docs/repository-structure.md](docs/repository-structure.md)
maps this repo onto them and lists the deliberate deviations.

```
repo-root/
├── services/
│   ├── api/                  ← the backend: one Python project, one Docker image, one deployment
│   │   ├── main.py           ← mounts all sub-apps, single FastAPI deployment
│   │   ├── common/           ← small shared helpers (settings, DB session, token verification)
│   │   ├── trips/
│   │   │   ├── api.py        ← FastAPI() sub-app for trips, own router(s)
│   │   │   ├── models.py
│   │   │   └── migrations/   ← own migration chain
│   │   ├── windsurf/
│   │   │   └── api.py        ← FastAPI() sub-app for windsurf (gets a migrations/ chain once it has tables)
│   │   └── Dockerfile
│   ├── trips-frontend/       ← SvelteKit SPA (adapter-static), its own Render static site
│   └── windsurf-frontend/    ← (not built yet)
├── tests/
│   ├── api/                  ← unit/ and integration/ mirror services/api/; acceptance/ is split by sub-app
│   └── trips-frontend/
├── scripts/                  ← seed, API-type generation, mock tokens, commit checks (never in images)
├── docker/                   ← compose defaults, WireMock mocks of external APIs, nginx config
├── docs/                     ← how-to guides
├── pyproject.toml, uv.lock   ← the api project
├── package.json              ← npm workspaces (one per frontend)
├── docker-compose.yml        ← local stack: db, migrate, api, external API mocks, frontends
├── render.yaml
├── CLAUDE.md
├── README.md
└── ARCHITECTURE.md           ← this file
```

Each sub-project keeps its **own Alembic migration chain and own data models** even though they share one running app — this keeps them genuinely independent at the data layer, so splitting into separate deployments later doesn't require untangling shared migrations.

In practice this means each sub-project's tables live in **their own Postgres schema** (e.g. `trips.trips`) within the one database, and each chain records its own progress in an `alembic_version` table inside that same schema — so the chains never collide, and a schema (plus its chain) can be lifted out on its own. There are **no foreign keys across schemas**, and no users table at all: users live in Clerk, so e.g. `trips.trips.owner_id` is just the Clerk user id from the token's `sub` claim.

Reasoning for monorepo (vs. separate repos per sub-project): for a solo/personal project, one repo keeps coordination simple (one PR can touch both an API and its frontend). Reuse of an API by other projects is about its **network interface** (the HTTP endpoints), not which repo the code lives in — so nothing is lost by keeping them together for now. Splitting into separate repos later, if ever needed, is a mechanical operation, not a redesign.

## Deployment (Render)

- **Backend** → **one** Render **Web Service** (container), paid (~$7/mo), runs the single FastAPI app (`api.main:app`) via uvicorn from `services/api/Dockerfile` — the same image docker compose runs locally, with migrations applied as Render's pre-deploy step — hosts all sub-APIs (`/trips/*`, `/windsurf/*`, etc.) from this one service
- **Frontends** → each deployed as its own Render **Static Site**, free, each built from its own workspace (`services/trips-frontend/`, `services/windsurf-frontend/`), serving the built Svelte files from a CDN

### Static site routing (SPA fallback)

Each Svelte frontend is a single static `index.html` + JS bundle. All routes (e.g. `/trips/paris`, `/trips/london`, `/login`) serve the **same `index.html`** — there is no per-route HTML file. Render needs a rewrite rule per static site so that unmatched paths don't 404:

- **Dashboard**: Settings → Redirects/Rewrites → Add Rule
  - Source: `/*`
  - Destination: `/index.html`
  - Action: **Rewrite** (not Redirect — Rewrite keeps the URL in the address bar intact, which the client-side router needs to read)

Or via `render.yaml`:
```yaml
routes:
  - type: rewrite
    source: /*
    destination: /index.html
```

Dynamic content (e.g. which trip, which place) is resolved **entirely client-side**: the router reads `window.location.pathname`, extracts the dynamic segment (e.g. `paris`), and the component fetches that specific data from the API. The static file itself never changes per route — only the JS behavior after it loads does.

## Auth

- Users sign up and sign in with **[Clerk](https://clerk.com)**. Clerk owns users, passwords and sessions; the backend has no login, password or user-record code at all.
- The frontend gets a short-lived (~60s) session token from Clerk's SDK and sends it on every API call as `Authorization: Bearer <token>`. Clerk keeps the long-lived session in its own httpOnly cookie, so nothing long-lived is readable by our JavaScript.
- A shared `authFetch()` helper in the frontend attaches the token and redirects to `/login` on a `401` response
- The backend **only verifies** tokens: RS256 signature against the issuer's published keys (JWKS), issuer, expiry, and authorized party (`azp`). The token's `sub` — a Clerk user id like `user_2ab…` — is trusted as the user id. Every sub-app verifies locally and never calls Clerk beyond fetching its public keys, so sub-apps stay independent.
- Agents send a bearer token the same way — no special-casing in the API (which Clerk machine-auth option agents use is still to be decided).
- CORS is configured once, on the single backend app, with an `allow_origins` list covering every frontend's origin (e.g. `trips.yourdomain.com`, `windsurf.yourdomain.com`). No cookies are sent to the API, so credentials stay disabled.
- Production needs a custom domain: Clerk production instances require one (e.g. Clerk on `clerk.yourdomain.com`, frontends on `trips.yourdomain.com`, the API on `api.yourdomain.com`).
- **Locally, Clerk is mocked** like every other external service: the `clerk-mock` compose service publishes a JWKS and long-lived tokens for dev users (`docker/wiremock/clerk/`), and the frontend's login page lists them. The backend runs exactly the same verification, just trusting the mock's issuer — there is no "auth off" switch that could leak into production.

## Testing

pytest, with three test types under `tests/api/` — full detail in [docs/testing.md](docs/testing.md):

- **Unit** — pure logic, no database or network; mirrors `services/api/`.
- **Integration** — code against a real Postgres (queries, constraints, migrations); mirrors `services/api/`.
- **Acceptance** — the whole app over HTTP, split by API, primarily **contract tests**: every response is validated against a hand-written JSON Schema, so the API surface that frontends and agents depend on can't change by accident.

Every test that needs a database gets a throwaway Postgres from **testcontainers** — never the dev database. External HTTP APIs (e.g. UKHO tides) are never called; the client is given a fake transport instead.

## Future option: SSR (not needed now)

If SEO or public-facing pages become a requirement later (none exist currently — this is an authenticated tool, not public content), the Svelte frontend(s) can be migrated from `adapter-static` to `adapter-node` (or similar) to add server-side rendering. This is a **config-level swap**, not a rewrite — route/component code stays largely the same. The tradeoff at that point: it requires a running server again (another paid Render service per frontend that needs it), lost when choosing static-only now.

## Key principle to carry forward

Each sub-project (`trips`, `windsurf`, etc.) is architecturally self-contained at the **code and data** level — own models, own Alembic migration chain, own FastAPI sub-app with its own `/docs` — but currently shares **one backend deployment** (single container, single Render Web Service) for cost/operational simplicity. Frontends remain separately deployed per sub-project (free static sites). The sub-apps are kept loosely coupled on purpose so that splitting any one of them out into its own standalone deployment later is a mechanical change (extract its folder, give it its own `main.py` and Render service), not a redesign.
