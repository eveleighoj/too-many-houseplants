# Deployment

Production runs on [Render](https://render.com) and signs users in with
[Clerk](https://clerk.com). GitHub drives every deploy. Replace `<domain>` below with the real
domain.

| What | Where | URL |
| --- | --- | --- |
| api (all sub-APIs) | Render web service `too-many-houseplants-api` (Docker, Frankfurt, paid) | `https://api.<domain>` |
| Postgres | Render database `too-many-houseplants-db` (Frankfurt, paid, private network only) | — |
| trips frontend | Render static site `trips-frontend` (free, CDN) | `https://trips.<domain>` |
| sign-in | Clerk production instance | `https://clerk.<domain>` (and `accounts.<domain>`) |

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

Render never deploys by itself (`autoDeployTrigger: "off"`). To redeploy without a new commit
(e.g. after changing an environment variable), use **Actions → Deploy → Run workflow**.

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

   | Service | Variable | Value |
   | --- | --- | --- |
   | api | `AUTH_ISSUER` | the Clerk production Frontend API URL, `https://clerk.<domain>` (step 4). To start before step 4, use the development instance's, `https://endless-yak-8528.clerk.accounts.dev` |
   | api | `AUTH_AUTHORIZED_PARTIES` | `https://trips.<domain>` |
   | api | `ALLOWED_ORIGINS` | `https://trips.<domain>` |
   | api | `UKHO_API_KEY` | your UKHO Admiralty API key. Leave empty for now and `/windsurf` returns 503 |
   | trips-frontend | `VITE_API_URL` | `https://api.<domain>` |
   | trips-frontend | `VITE_CLERK_PUBLISHABLE_KEY` | the Clerk production publishable key, `pk_live_…` (step 4); the `pk_test_…` one to start |

   `DATABASE_URL` is filled in automatically from the database.
4. **Apply.** Render creates the database and both services, and deploys them once. Check
   the api's logs: migrations ran, then `/healthz` passes.
5. Note each service's id (`srv-…`, in its URL or Settings) for step 5.

### 3. Domains for the api and frontend

For each service, go to **Settings → Custom Domains → Add**:

| Service | Domain | DNS record at your provider |
| --- | --- | --- |
| api | `api.<domain>` | `CNAME api → <the target Render shows>` |
| trips-frontend | `trips.<domain>` | `CNAME trips → <the target Render shows>` |

Render verifies them and issues HTTPS certificates automatically. Until DNS is set up, the
services are also reachable on their `*.onrender.com` URLs.

### 4. Clerk production instance

A production instance is a separate copy of the Clerk application, with its own users and
settings.

1. In the Clerk dashboard, **Deploy to production**, then enter `<domain>`.
2. Add the DNS records Clerk lists at your provider: `clerk.<domain>`, `accounts.<domain>`,
   and email records such as `clkmail` and the DKIM keys. Wait until Clerk shows them as
   verified.
3. Configure the production instance like development:
   - **Sign-in methods:** email address + password. Social logins such as Apple or Google
     need your **own** credentials in production.
   - **Sign-up mode: invite-only.** Every signed-in user can see every trip
     ([trips.md](trips.md#access-a-trusted-group-of-friends-for-now)), so this is what keeps
     the data private.
   - **Users:** invite or create the people who should have access.
4. Put the production values into Render, and redeploy (Actions → Deploy → Run workflow):
   - api: `AUTH_ISSUER=https://clerk.<domain>`
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
   | `TRIPS_FRONTEND_URL` | the frontend's URL (`https://trips.<domain>`, or its `*.onrender.com` URL until then), shown on each GitHub deployment |

### 6. First deploy and checks

Run **Actions → Deploy → Run workflow**, then check:

- `https://api.<domain>/healthz` returns `{"status":"ok"}`
- `https://api.<domain>/trips/` without a token returns **401**
- `https://trips.<domain>` redirects to `/login` and shows Clerk's sign-in; once signed in,
  you see the trips list (empty in production: the seed only runs locally)
- GitHub's repo page shows a successful **production** deployment.

## Costs

Paid on Render: the api web service (`starter`) and the database (`0.1c-256mb`). Static sites
are free. Clerk's free plan covers this. Check Render's pricing page for current amounts.
