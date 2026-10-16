# Frontends

Each frontend is its own SvelteKit app in its own top-level folder (`trips-frontend/`, and
later e.g. `windsurf-frontend/`). Each is built to static files and hosted as its own free
Render static site. Each is just a client of the backend API, the same as an agent (see
[ARCHITECTURE.md](../ARCHITECTURE.md)).

## How a frontend is built

- **SvelteKit with `adapter-static` in SPA mode.** `ssr = false` in `src/routes/+layout.ts`
  and `fallback: 'index.html'` in `vite.config.ts`. Every URL serves the same `index.html`,
  and the client-side router renders the page. Hosts must rewrite unknown paths to
  `/index.html` (`render.yaml` does this). Moving to SSR later means swapping to
  `adapter-node`; that's a config change, not a rewrite.
- **Svelte 5 runes** (`$state`, `$derived`, `$props`, `$effect`) throughout.
- **TypeScript.** Import `src/lib` through the `#lib` alias **with the file extension**, e.g.
  `import { auth } from '#lib/auth.svelte.ts'`. The alias is a Node subpath import, which
  only resolves exact paths.

## trips-frontend

```
trips-frontend/
├── src/
│   ├── app.css               ← colour tokens (light + dark) and base styles
│   ├── lib/
│   │   ├── config.ts         ← API_URL, from VITE_API_URL
│   │   ├── auth.svelte.ts    ← the token: reactive state + localStorage (dev login; Clerk to come)
│   │   ├── token.ts          ← pure token helpers (expiry, safe ?next= redirects)
│   │   ├── navigation.ts     ← goToLogin()
│   │   ├── trips.ts          ← pure display helpers (dates, nights, booking filters, map links)
│   │   ├── api/
│   │   │   ├── client.ts     ← authFetch() and one function per endpoint
│   │   │   ├── types.ts      ← friendly names for the API's types
│   │   │   ├── devUsers.ts   ← clerk-mock's dev users (local login only)
│   │   │   └── trips.d.ts    ← GENERATED from the backend's OpenAPI spec
│   │   └── components/       ← TripDetails, PlaceInfo, BookingInfo
│   └── routes/
│       ├── +page.svelte      ← your trips + create a trip (needs login)
│       ├── login/            ← log in (clerk-mock's dev users locally), then back to ?next=
│       └── trips/[id]/       ← one trip; works logged out (redacted view)
└── tests/                    ← see Testing below
```

### Talking to the API

- **Call the API only through the functions in `src/lib/api/client.ts`.** They all go
  through `authFetch()`, which attaches `Authorization: Bearer <token>`. On a 401 it logs
  the user out and redirects to `/login?next=<current page>`, then throws
  `UnauthorizedError`. Callers ignore that error, because the redirect has already
  happened.
- **Logging in:** users sign in with Clerk (see ARCHITECTURE.md → Auth). Until a Clerk
  application is configured, the login page only works locally:
  - With `VITE_MOCK_AUTH_URL` set (compose sets it to clerk-mock), it lists clerk-mock's dev
    users, and picking one stores that user's token.
  - Without it, it says sign-in isn't configured.

  Never set `VITE_MOCK_AUTH_URL` in a production build.
- **The token is kept in `localStorage`** (`trips.token`), as ARCHITECTURE.md decides. An
  expired token counts as logged out.
- **Anyone can open a trip page.** Logged out, or as someone who isn't the owner, the API
  returns the redacted view (`stays`/`bookings` are `null`) and `TripDetails` explains
  what's hidden.

### API types are generated, never written by hand

`src/lib/api/trips.d.ts` is generated from the running backend's OpenAPI
specs, so the frontend's types always match the API. After any backend API change:

```bash
make up          # the backend must be running
make api-types   # = cd trips-frontend && npm run api:types
npm run check    # type errors now show everywhere the API change matters
```

Commit the regenerated files. Prettier and ESLint ignore them.

## Running it

| How | URL | Notes |
| --- | --- | --- |
| `make up` | http://localhost:5173 | The compose `trips-frontend` service: Vite dev server with hot reload. Its `node_modules` live in a Docker volume, not your checkout. |
| `cd trips-frontend && npm run dev` | http://localhost:5173 | On the host. Needs `npm ci` first (`make init` does it). Stop the compose service first: they share the port. |

The backend must allow the frontend's origin: `ALLOWED_ORIGINS` in `backend/.env` includes
`http://localhost:5173`.

After `make seed`, log in by picking the Demo or Friend dev user.

## Testing

Tests live in `trips-frontend/tests/`, never next to the code, following the same rule as
the backend:

| Folder | Runs in | For |
| --- | --- | --- |
| `tests/unit/` | Node | pure functions in `src/lib` (`trips.ts`, `token.ts`) and the API client, with `fetch` stubbed |
| `tests/component/` | real headless Chromium (Vitest browser mode + Playwright) | components, rendered with `vitest-browser-svelte` |
| `tests/fixtures.ts` | — | builders for API shapes (`makeTrip`, `makePlace`, `redacted(trip)`, …), typed against the generated API types, so a breaking API change breaks the fixtures |

```bash
make test-trips-frontend    # or: cd trips-frontend && npm test
npx vitest --project unit   # one project, in watch mode
```

Name tests with `describe('<function or Component>')` and `test('<behaviour>')`. This
mirrors the backend's `test_<function>_<behaviour>`.

Tests never call the real API. Unit tests stub `fetch`, and component tests pass data
straight in as props.

## Hosting

`render.yaml` defines `trips-frontend` as a free static site:
- it runs `npm ci && npm run build` in `trips-frontend/` and publishes `build/`
- it rewrites `/*` to `/index.html`
- it rebuilds only when `trips-frontend/**` changes.

Set `VITE_API_URL` to the API's public URL, which is baked in at build time. Add the site's
URL to the backend's `ALLOWED_ORIGINS`.

## Adding another frontend

1. Scaffold it next to `trips-frontend/`:

   ```bash
   npx sv@1.1.1 create <name>-frontend --template minimal --types ts \
     --add prettier eslint "vitest=usages:unit,component" "sveltekit-adapter=adapter:static" \
     --install npm
   ```

2. Copy the SPA setup from trips-frontend:
   - `ssr = false` in `src/routes/+layout.ts`
   - `fallback: 'index.html'` in `vite.config.ts`
   - the `tests/` folder layout and test projects in `vite.config.ts`.

   Copy `src/lib/{config,auth.svelte,token,navigation}.ts` and the `authFetch` part of
   `api/client.ts` as well. Each frontend owns its copy, so frontends stay independently
   deployable.
3. Add `scripts/generate-api-types.js`, listing the APIs it uses.
4. Add a compose service like `trips-frontend`, on a new port, and add that origin to
   `ALLOWED_ORIGINS`.
5. Add a `render.yaml` static site like `trips-frontend`, and Makefile targets like
   `test-trips-frontend`.
