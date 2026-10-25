# too-many-houseplants

A personal JSON API, written in FastAPI, that backs several small projects. Each project's API is
its own mounted sub-app with its own `/docs`, all served from one deployment. Svelte
frontends, and agents, are both just clients of it. Users sign in with
[Clerk](https://clerk.com); locally a Clerk mock stands in, so no account is needed.

| API      | Docs              | What it does                                                  |
| -------- | ----------------- | ------------------------------------------------------------- |
| Trips    | `/trips/docs`     | Trip itineraries; dates/bookings only visible to the owner    |
| Windsurf | `/windsurf/docs`  | 7-day tide windows for windsurfing spots (UKHO tidal API)     |

## Quick start

Needs [uv](https://docs.astral.sh/uv/), Node 24 and Docker. Run everything from the repo root.

```bash
make setup                              # install everything, create .env
make up                                 # API on http://localhost:8000, trips frontend on http://localhost:5173
make seed                               # demo trips; log in as a dev user (see docs/local-development.md)
make test
```

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md): why it's built this way
- [docs/local-development.md](docs/local-development.md): running it, docker compose
- [docs/repository-structure.md](docs/repository-structure.md): where everything lives, and why
- [docs/api.md](docs/api.md): the api service: sub-apps, auth, settings
- [docs/frontend.md](docs/frontend.md): the Svelte frontends (trips-frontend)
- [docs/testing.md](docs/testing.md): the tests/ layout; unit, integration and acceptance (contract) tests
- [docs/trips.md](docs/trips.md): the trips data model (places, stops, stays, bookings)
- [docs/contributing.md](docs/contributing.md): Conventional Commits, rebasing, CI
- [docs/deployment.md](docs/deployment.md): production on Render and Clerk, and how deploys happen
- [docs/migrations.md](docs/migrations.md): Alembic chains, making schema changes
