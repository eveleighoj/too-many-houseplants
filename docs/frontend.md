# Frontends

Each frontend is its own SvelteKit app in `services/<name>-frontend/` (`trips-frontend` now,
later e.g. `windsurf-frontend`), and an **npm workspace** of the root `package.json`: one
lockfile and one `node_modules` at the repo root
([repository-structure.md](repository-structure.md)). Each is built to static files and
hosted as its own free Render static site. Each is just a client of the api, the same as an
agent (see [ARCHITECTURE.md](../ARCHITECTURE.md)).

## How a frontend is built

- **SvelteKit with `adapter-static` in SPA mode.** `ssr = false` in `src/routes/+layout.ts`
  and `fallback: 'index.html'` in `vite.config.ts`. Every URL serves the same `index.html`,
  and the client-side router renders the page. Hosts must rewrite unknown paths to
  `/index.html` (`render.yaml` and `docker/nginx-spa.conf` do this). Moving to SSR later means
  swapping to `adapter-node`; that's a config change, not a rewrite.
- **Svelte 5 runes** (`$state`, `$derived`, `$props`, `$effect`) throughout.
- **TypeScript.** Inside the app, import `src/lib` through the `#lib` alias **with the file
  extension**, e.g. `import { mapLinks } from '#lib/trips.ts'`. The alias is a Node subpath
  import (SvelteKit 3's replacement for `$lib`), which only resolves exact paths. Tests, which
  live outside the app, import it by package name instead (see Testing).

## trips-frontend

```
services/trips-frontend/
├── package.json              ← the workspace: its app dependencies and scripts
├── vite.config.ts            ← SvelteKit + shared test settings
├── vitest.unit.config.ts     ← test project: unit tests, in Node
├── vitest.components.config.ts ← test project: component tests, in headless Chromium
├── Dockerfile                ← the static build served by nginx (local / e2e use)
├── src/
│   ├── app.css               ← colour tokens (light + dark) and base styles
│   ├── lib/
│   │   ├── config.ts         ← API_URL, from VITE_API_URL
│   │   ├── auth/             ← sign-in behind one interface (see Signing in)
│   │   │   ├── provider.ts   ← the AuthProvider interface the app uses
│   │   │   ├── index.ts      ← picks the provider for this build; exports `auth`
│   │   │   ├── clerk.svelte.ts ← Clerk (production, or locally against a Clerk dev instance)
│   │   │   ├── mock.svelte.ts ← clerk-mock's dev users (local)
│   │   │   └── none.ts       ← no sign-in configured
│   │   ├── token.ts          ← pure token helpers (expiry, safe ?next= redirects)
│   │   ├── navigation.ts     ← goToLogin()
│   │   ├── trips.ts          ← pure display helpers (dates, nights, booking filters, map links)
│   │   ├── api/
│   │   │   ├── client.ts     ← authFetch() and one function per endpoint
│   │   │   ├── types.ts      ← friendly names for the API's types
│   │   │   ├── devUsers.ts   ← clerk-mock's dev users (local login only)
│   │   │   └── trips.d.ts    ← GENERATED from the api's OpenAPI spec
│   │   └── components/       ← TripDetails, PlaceInfo, BookingInfo, DevLogin
│   └── routes/
│       ├── +page.svelte      ← your trips + create a trip (needs login)
│       ├── login/            ← log in (clerk-mock's dev users locally), then back to ?next=
│       └── trips/[id]/       ← one trip
└── static/
```

Dependencies: `npm install <pkg> -w services/trips-frontend`. Lint and test tooling (ESLint,
Prettier, Vitest, Playwright) is shared, in the root `package.json`, with its config at the root.

### Talking to the API

- **Call the API only through the functions in `src/lib/api/client.ts`.** They all go
  through `authFetch()`, which attaches `Authorization: Bearer <token>`. On a 401 it logs
  the user out and redirects to `/login?next=<current page>`, then throws
  `UnauthorizedError`. Callers ignore that error, because the redirect has already
  happened.
- **Every page except `/login` needs sign-in.** `+layout.svelte` sends signed-out visitors
  to `/login?next=<page>` and doesn't render the page until someone is signed in, so nothing
  is fetched for them. Signed in, you see every trip (see [trips.md](trips.md#access-a-trusted-group-of-friends-for-now)).

### Signing in

The app only talks to the `AuthProvider` interface (`src/lib/auth/provider.ts`) through
`import { auth } from '#lib/auth/index.ts'`. Only `src/lib/auth/` knows which provider is
behind it, so switching provider (Clerk → anything else) means writing one new implementation.

| `auth.` | Meaning |
| --- | --- |
| `kind` | `'clerk'`, `'mock'` or `'none'` |
| `loaded` | false until the provider knows whether someone is signed in. Clerk loads asynchronously, so **wait for `loaded` before redirecting to /login** |
| `signedIn` | someone is signed in (reactive) |
| `getToken()` | a bearer token for the API, or null. Call it for every request: Clerk's tokens last about a minute and it refreshes them. `authFetch` does this for you |
| `signOut()` | sign out |

Which provider a build gets (`chooseAuthKind` in `index.ts`):

| Build | Provider | Login page |
| --- | --- | --- |
| `VITE_CLERK_PUBLISHABLE_KEY` set (production; or locally, see [local-development.md](local-development.md#signing-in-with-your-clerk-development-instance)) | `clerk` | Clerk's sign-in form; afterwards Clerk navigates to `?next=` |
| otherwise, `VITE_MOCK_AUTH_URL` set (compose sets it to clerk-mock) | `mock` | lists clerk-mock's dev users; picking one stores their token in `localStorage` (`trips.token`) |
| nothing configured | `none` | says sign-in isn't configured; public pages still work |

Never set `VITE_MOCK_AUTH_URL` in a production build.

#### How Clerk is loaded

`ClerkAuth` loads Clerk's SDK and its prebuilt UI as **scripts from the Clerk instance's own
domain** (worked out from the publishable key), the way Clerk's script-tag setup does, rather
than bundling them:

- Clerk's browser build is ~85 KB and fetches the rest on demand. Bundling `@clerk/clerk-js`
  from npm would add ~500 KB (compressed) to the app.
- Bundling Clerk's UI (`@clerk/ui`) would pull React into the app.

Both scripts are pinned to exact versions: `CLERK_JS_VERSION` and `CLERK_UI_VERSION` in
`src/lib/auth/clerk.svelte.ts`. `@clerk/clerk-js` is only a dev dependency, for its TypeScript
types, so **when you update it, update `CLERK_JS_VERSION` to the same version** (and
`CLERK_UI_VERSION` to the matching `@clerk/ui`). Clerk's sign-in steps use the URL hash, so
`/login` needs no extra routes.

### API types are generated, never written by hand

`src/lib/api/trips.d.ts` is generated from the api's OpenAPI spec, so the frontend's types
always match the API. After any api change:

```bash
make api-types        # from the running api (make up first); or `make api-types-check`, no server needed
npm run lint          # the type check now shows everywhere the API change matters
```

Commit the regenerated files. Prettier and ESLint ignore them. CI's `api-types` job fails if
they're out of date. The generator is `scripts/trips-frontend/generate-api-types.js`.

## Running it

| How | URL | Notes |
| --- | --- | --- |
| `make up` | http://localhost:5173 | The compose `trips-frontend` service: Vite dev server with hot reload. Its `node_modules` live in Docker volumes, not your checkout. |
| `npm run dev -w services/trips-frontend` | http://localhost:5173 | On the host, from the repo root (`make setup` installs everything). Stop the compose service first: they share the port. |

The api must allow the frontend's origin: `ALLOWED_ORIGINS` in `.env` includes
`http://localhost:5173`.

After `make seed`, log in by picking the Demo or Friend dev user.

## Testing

A frontend's tests live in `tests/<frontend>/`, never next to the code
([repository-structure.md](repository-structure.md)), named `*.test.ts`:

| Folder | Runs in | For |
| --- | --- | --- |
| `tests/trips-frontend/unit/` | Node | pure functions in `src/lib` (`trips.ts`, `token.ts`) and the API client, with `fetch` stubbed |
| `tests/trips-frontend/unit/components/` | real headless Chromium (Vitest browser mode + Playwright) | components, rendered with `vitest-browser-svelte` |
| `tests/trips-frontend/fixtures.ts` | — | builders for API shapes (`makeTrip`, `makePlace`, `makeBooking`, …), typed against the generated API types, so a breaking API change breaks the fixtures |

Tests import the app through its **workspace package name**, because `#lib` only resolves
inside the app's own folder:

```ts
import { mapLinks } from 'trips-frontend/src/lib/trips.ts';
import TripDetails from 'trips-frontend/src/lib/components/TripDetails.svelte';
```

```bash
make test-frontends                                 # = npm test: every frontend's projects
npx vitest --project trips-frontend:unit            # one project, in watch mode
```

The root `vitest.config.ts` runs every `services/*-frontend/vitest.*.config.ts` project.
Every test folder also has an empty `__init__.py`: the repo-wide rule from
[testing.md](testing.md), harmless for TypeScript.

Name tests with `describe('<function or Component>')` and `test('<behaviour>')`. This
mirrors the api's `test_<function>_<behaviour>`.

Tests never call the real API. Unit tests stub `fetch`, and component tests pass data
straight in as props.

## Hosting

`render.yaml` defines `trips-frontend` as a free static site:
- it runs `npm ci && npm run build -w services/trips-frontend` from the repo root and
  publishes `services/trips-frontend/build/`
- it rewrites `/*` to `/index.html`
- it rebuilds only when the app or the root `package.json` / lockfile changes.

Set `VITE_API_URL` to the API's public URL, which is baked in at build time. Add the site's
URL to the api's `ALLOWED_ORIGINS`.

## Adding another frontend

1. Scaffold it in `services/`:

   ```bash
   npx sv@1.1.1 create services/<name>-frontend --template minimal --types ts \
     --add "sveltekit-adapter=adapter:static" --no-install
   ```

   Delete its lint/test tooling (it's shared at the root) and its lockfile, and add it to
   `workspaces` in the root `package.json`, then `npm install` from the root.
2. Copy the setup from trips-frontend:
   - `ssr = false` in `src/routes/+layout.ts`, and `fallback: 'index.html'` in `vite.config.ts`
   - `vite.config.ts`'s `test.dir`, and both `vitest.*.config.ts` files (renamed for the new app)
   - `src/lib/{config,token,navigation}.ts`, `src/lib/auth/`, and the `authFetch` part of
     `api/client.ts`. Each frontend owns its copy, so frontends stay independently deployable.
   - the `Dockerfile`, pointing at the new app.
3. Create `tests/<name>-frontend/unit/` with an `__init__.py` in each folder.
4. Add `scripts/<name>-frontend/generate-api-types.js`, listing the APIs it uses, and its
   `api:types` script.
5. Add a compose service like `trips-frontend`, on a new port, and add that origin to
   `ALLOWED_ORIGINS`.
6. Add a `render.yaml` static site like `trips-frontend`, and add the app to the
   `api-types` Makefile target.
