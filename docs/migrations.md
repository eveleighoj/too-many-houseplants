# Database migrations

Every sub-app with tables has its **own Alembic chain** and its **own Postgres schema**,
all in one database:

| Chain | Schema | Config |
| --- | --- | --- |
| trips | `trips` | `services/api/trips/alembic.ini` |

Each chain records its progress in an `alembic_version` table **inside its own schema**
(`trips.alembic_version`), so chains never collide. A sub-app's schema and chain can then
be moved to its own database later without untangling anything.

## Making a schema change

**Always generate migrations with Alembic. Don't write them by hand.**

1. Change the SQLAlchemy models in `services/api/<chain>/models.py`.
2. Make sure your local database is running and up to date (`make up`, or `make db-up` then
   `make migrate`). Autogenerate compares the models against that database.
3. Generate the migration:

   ```bash
   make migration chain=trips m="add cover image"
   ```

   This writes `services/api/trips/migrations/versions/<rev>_add_cover_image.py`. A
   post-write hook runs ruff on it automatically.
4. **Read the generated file.** Autogenerate doesn't spot renames (it emits drop + add),
   and it can't write data migrations. Fix those by hand. Make sure `downgrade()` reverses
   `upgrade()`.
5. Apply it with `make migrate`. Run the integration tests: they check that every chain
   upgrades, downgrades to base and back, and leaves **no drift** between models and
   migrations (`alembic check`). A forgotten migration fails them.

## Adding a chain for a new sub-app

1. Give the models their own schema:

   ```python
   SCHEMA = "<name>"


   class Base(DeclarativeBase):
       metadata = MetaData(schema=SCHEMA)
   ```

2. Copy `trips/alembic.ini` and `trips/migrations/` (`env.py` and `script.py.mako`, not
   `versions/`) into the new sub-app. Update the comment in `alembic.ini`, and the import in
   `env.py`:

   ```python
   from api.<name>.models import SCHEMA, Base
   ```

3. Add the name to `CHAINS` in `services/api/common/migrations.py`. That one list drives
   `make migrate`, the compose `migrate` service, Render's pre-deploy step and the test
   database setup.
4. Generate the first migration: `make migration chain=<name> m="create <name> tables"`.

## Where migrations run

| Where | How |
| --- | --- |
| docker compose | the one-shot `migrate` service runs before `api` starts |
| host | `make migrate` (uses `DATABASE_URL` from `.env`) |
| tests | `tests/conftest.py` runs every chain against a fresh testcontainers database |
| Render | `preDeployCommand` in `render.yaml`; a failed migration stops the deploy |

All of them call `api.common.migrations.upgrade_all()`. It takes a Postgres advisory lock
around each chain, so two containers starting at once (a rolling deploy, a scale-up) take
turns instead of migrating at the same time. Alembic has no lock of its own.

Migrations ship inside the `api` package (they're in the wheel), so the production image can
run them with no source checkout: `python -m api.common.migrations`.
