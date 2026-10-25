# Deployment

Production runs on [Render](https://render.com) and signs users in with
[Clerk](https://clerk.com). GitHub drives every deploy. The domain is
`wehavetoomanyhouseplants.co.uk`, with its DNS at **Cloudflare**.

| What | Where | URL |
| --- | --- | --- |
| api (all sub-APIs) | Render web service `too-many-houseplants-api` (Docker, Frankfurt, paid) | `https://api.wehavetoomanyhouseplants.co.uk` |
| Postgres | Render database `too-many-houseplants-db` (Frankfurt, paid, private network only) | — |
| trips frontend | Render static site `trips-frontend` (free, CDN) | `https://trips.wehavetoomanyhouseplants.co.uk` |
| sign-in | Clerk production instance | `https://clerk.wehavetoomanyhouseplants.co.uk` (and `accounts.wehavetoomanyhouseplants.co.uk`) |

Everything on Render is defined in `render.yaml`.

## How a deploy happens

1. A PR merges to `main`, and **Test** runs on `main`.
2. When Test passes, **Deploy** (`.github/workflows/deploy.yml`) deploys that exact commit:
   - the **api first**: Render builds `services/api/Dockerfile`, runs migrations
     (`preDeployCommand`; a failed migration stops the deploy), then switches over once
     `/healthz` answers
   - then **trips-frontend**: `npm ci` and the build, with `VITE_*` values baked in.

   Each step waits for Render's result, and the job fails if a deploy fails.
3. **Logs stay in Render.** This repo is public, so its Actions logs are too. Render's logs can
   contain visitors' IP addresses, request URLs and error details, so the workflow writes
   Render's output to a file that never leaves the runner and only reports the result. When a
   deploy fails, the job says which service; the details are in the Render dashboard
   (service → **Events** / **Logs**).
4. GitHub records it as a deployment of the **production** environment (repo homepage →
   Deployments), with its status and URL. Nobody needs Render access to see what's live, or
   whether a deploy worked; only investigating a failure needs Render.

Render never deploys by itself (`autoDeployTrigger: "off"`, and the Blueprint's auto-sync is
off). To redeploy without a new commit (e.g. after changing an environment variable), use
**Actions → Deploy → Run workflow**.

**Changing `render.yaml`** (services, plans, domains, variables' keys): after the change
merges and Test passes on `main`, open the Blueprint in Render and click **Manual Sync**. Render
shows what will change, applies it, and redeploys the services it changed. Removing something
from the file never deletes it (delete it in Render yourself), and the database's region,
Postgres version and name can't change after creation.

**Rolling back:** revert the commit on `main` (Test and Deploy then ship the revert), or, in an
emergency, use Render's **Rollback** on the service's deploy history. Migrations aren't
rolled back automatically.

## One-time setup

Do these in order. Steps 3 and 4 need DNS changes at your domain's DNS provider. They can
take a while to propagate.

### 1. Merge the hosting branch

`render.yaml` and the Deploy workflow must be on `main`.

### 2. Render: create everything from the Blueprint

1. Create a Render account, and connect your GitHub account (Render needs read access to this
   repository).
2. **New → Blueprint**, then choose this repository. Render reads `render.yaml` and lists the
   database and both services.
3. Fill in the values it asks for (the `sync: false` variables). You can change them later
   in each service's **Environment** tab:

   You start on Render's own `*.onrender.com` addresses and the Clerk **development** instance.
   Steps 3 and 4 switch to the domain and to Clerk production. Render shows each service's
   address once it's created. If a value isn't known yet, enter a placeholder and fix it before
   the first real deploy (step 6).

   | Service | Variable | To start | Final (after steps 3–4) |
   | --- | --- | --- | --- |
   | api | `AUTH_ISSUER` | `https://endless-yak-8528.clerk.accounts.dev` | `https://clerk.wehavetoomanyhouseplants.co.uk` |
   | api | `AUTH_AUTHORIZED_PARTIES` | the frontend's `https://….onrender.com` address | `https://trips.wehavetoomanyhouseplants.co.uk` |
   | api | `ALLOWED_ORIGINS` | the frontend's `https://….onrender.com` address | `https://trips.wehavetoomanyhouseplants.co.uk` |
   | api | `UKHO_API_KEY` | empty (`/windsurf` returns 503) | your UKHO Admiralty API key, when you have one |
   | trips-frontend | `VITE_API_URL` | the api's `https://….onrender.com` address | `https://api.wehavetoomanyhouseplants.co.uk` |
   | trips-frontend | `VITE_CLERK_PUBLISHABLE_KEY` | `pk_test_ZW5kbGVzcy15YWstODUyOC5jbGVyay5hY2NvdW50cy5kZXYk` | the production `pk_live_…` key |

   `DATABASE_URL` is filled in automatically from the database.
4. **Deploy Blueprint.** Render creates the database and both services (with their custom
   domains), and deploys each once. Check the api's logs: migrations ran, then `/healthz`
   passes.
5. **Turn off the Blueprint's auto-sync:** Blueprint → **Settings → Auto Sync: No**. With it
   on, every change to `render.yaml` reaching `main` would be applied *and deployed* straight
   away, bypassing the Deploy workflow (and possibly before Test has passed).
6. Note each service's id (`srv-…`, in its URL or Settings) for step 5.

### 3. Domains for the api and frontend

`render.yaml` already declares both custom domains, so the Blueprint adds them to Render.
Each needs a record in **Cloudflare → DNS → Records** before Render can verify it. Until then,
the service's **Settings → Custom Domains** shows it as unverified:

| Service | Domain (in `render.yaml`) | Cloudflare record |
| --- | --- | --- |
| api | `api.wehavetoomanyhouseplants.co.uk` | `CNAME`, name `api`, target the api's `….onrender.com` host Render shows, **DNS only** |
| trips-frontend | `trips.wehavetoomanyhouseplants.co.uk` | `CNAME`, name `trips`, target the static site's `….onrender.com` host Render shows, **DNS only** |

Cloudflare specifics:

- **Proxy status: DNS only (grey cloud).** Render verifies the domain and issues its HTTPS
  certificate by reaching the service directly. Cloudflare's proxy (orange cloud) would
  intercept that. Leave it grey. You *can* proxy later, once Render shows the certificates as
  issued, but then SSL/TLS mode must be **Full**. There's no need to.
- **No `AAAA` records** for these names: Render doesn't support IPv6 yet.

Render verifies them and issues certificates within minutes of the records existing. Then
update the URLs everywhere (Render variables, and the GitHub `TRIPS_FRONTEND_URL` variable),
and redeploy:

| Where | Variable | Value |
| --- | --- | --- |
| api | `ALLOWED_ORIGINS`, `AUTH_AUTHORIZED_PARTIES` | `https://trips.wehavetoomanyhouseplants.co.uk` |
| trips-frontend | `VITE_API_URL` | `https://api.wehavetoomanyhouseplants.co.uk` |
| GitHub (repository variable) | `TRIPS_FRONTEND_URL` | `https://trips.wehavetoomanyhouseplants.co.uk` |

### 4. Clerk production instance

A production instance is a separate copy of the Clerk application, with its own users and
settings.

1. In the Clerk dashboard, **Deploy to production**, then enter `wehavetoomanyhouseplants.co.uk`.
2. In Clerk's **Domains** page, it lists the DNS records it needs: `clerk` (the Frontend
   API), `accounts` (the account portal), and email records such as `clkmail` and two DKIM
   keys. Add each one in Cloudflare exactly as shown, all as `CNAME`, **DNS only**. Clerk's
   check fails if they're proxied. Wait until Clerk shows them all as verified (usually
   minutes; up to 48 hours), then click **Deploy certificates**.
3. Configure the production instance like development:
   - **Sign-in methods:** email address + password. Social logins such as Apple or Google
     need your **own** credentials in production.
   - **Sign-up mode: invite-only.** Every signed-in user can see every trip
     ([trips.md](trips.md#access-a-trusted-group-of-friends-for-now)), so this is what keeps
     the data private.
   - **Users:** invite or create the people who should have access.
4. Put the production values into Render, and redeploy (Actions → Deploy → Run workflow):
   - api: `AUTH_ISSUER=https://clerk.wehavetoomanyhouseplants.co.uk`
   - trips-frontend: `VITE_CLERK_PUBLISHABLE_KEY=pk_live_…`

### 5. GitHub: the `production` environment and deploy settings

Until this step is done, the Deploy workflow **skips** every run instead of failing, so merging
to `main` before Render exists is fine.

1. **Settings → Environments → New environment**: create **`production`**, then add an
   **environment secret**:

   | Secret | Value |
   | --- | --- |
   | `RENDER_API_KEY` | a Render API key (Render → Account settings → API keys). It can act on everything in your Render account, so it's stored only in this environment |

   Under the environment's **deployment branches**, allow only `main`.
2. **Settings → Secrets and variables → Actions → Variables → New repository variable**: these
   are identifiers, not credentials. They're **repository** variables, because the workflow
   checks them before entering the environment:

   | Variable | Value |
   | --- | --- |
   | `RENDER_API_SERVICE_ID` | the api's `srv-…` id. Setting this turns deploys on |
   | `RENDER_TRIPS_FRONTEND_SERVICE_ID` | trips-frontend's `srv-…` id |
   | `TRIPS_FRONTEND_URL` | the frontend's URL (`https://trips.wehavetoomanyhouseplants.co.uk`, or its `*.onrender.com` URL until then), shown on each GitHub deployment |

### 6. First deploy and checks

Run **Actions → Deploy → Run workflow**, then check:

- `https://api.wehavetoomanyhouseplants.co.uk/healthz` returns `{"status":"ok"}`
- `https://api.wehavetoomanyhouseplants.co.uk/trips/` without a token returns **401**
- `https://trips.wehavetoomanyhouseplants.co.uk` redirects to `/login` and shows Clerk's sign-in; once signed in,
  you see the trips list (empty in production: the seed only runs locally)
- GitHub's repo page shows a successful **production** deployment.

## Costs

Approximate monthly costs, from third-party write-ups of Render's pricing in 2026. Render shows
the exact price when you create each resource.

| What | Plan | About |
| --- | --- | --- |
| api web service | `starter` (512 MB, 0.5 CPU) | $7 |
| Postgres | Basic 256 MB (`0.1c-256mb`), 1 GB storage (`diskSizeGB: 1`) | $6–7, plus about $0.30 for storage |
| trips frontend | static site | free |
| Render workspace | Hobby (one person) | free, with about 5 GB/month of bandwidth included |
| Clerk | free plan | free |
| Cloudflare DNS, GitHub Actions (public repo) | — | free |

**About $13–14 a month in total.** Storage is set to 1 GB (`render.yaml`) rather than Basic's
default 15 GB. It can be increased later, never decreased.
