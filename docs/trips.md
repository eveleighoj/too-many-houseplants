# Trips: domain model

The trips sub-app (`services/api/trips/`, Postgres schema `trips`) has these tables:

```
places ◄──────────────┬──────────────┬──────────────┐
  owner_id            │ place_id     │ place_id     │ place_id
                      │              │              │
trips ──► trip_days ──► stops        │              │
  owner_id │                ▲        │              │
           ├──► stays ──────┼────────┘              │
           │      ▲         │ stop_id (optional)    │
           │      │ stay_id (optional)              │
           └──► bookings ───────────────────────────┘
```

| Table | What it is |
| --- | --- |
| `places` | **All geographic data** lives here: name, lat/lng, an optional address, and optional `google_place_id` / `apple_place_id`. Nothing else stores coordinates. |
| `trips` | A trip, owned by a user (`owner_id` = the token's `sub`, a Clerk user id). |
| `trip_days` | Day 1, 2, … of a trip, each with a date. `(trip_id, day_number)` is unique. |
| `stops` | A place visited on a day, ordered by `sort_order`. |
| `stays` | Where you sleep: one place for `nights` consecutive nights, starting on the night of day `first_night`. For example, `first_night=3, nights=2` covers the nights of days 3 and 4. Both must be ≥ 1. |
| `bookings` | A reservation on a trip. It **must** be at a place, and can optionally be for one stop **or** one stay, never both. A ferry between two days is a booking for neither. |

## Rules

- **Places are owned per user** (`places.owner_id`, a Clerk user id). A trip's stops, stays and bookings
  should only use places with the same owner. The database doesn't enforce this, so code
  that creates them must check it. Because places are per user, private places never leak
  to other users, and editing a place never affects anyone else's trips.
- **Deleting:**
  - Deleting a trip removes its days, stops, stays and bookings, but **not** its places.
  - A place can't be deleted while a stop, stay or booking still uses it (`RESTRICT`).
  - Deleting a stop or stay keeps its bookings, but detaches them (`SET NULL`).
- **Map links:** the API turns `google_place_id` and `apple_place_id` into `googleMapsUrl` and
  `appleMapsUrl`. Store only the ids, never the URLs.
- **Redaction:** anyone who isn't the trip's owner (including anonymous callers) gets:
  - `date: null` on every day
  - `stays: null` and `bookings: null` (`null` means "hidden", unlike `[]`, which means
    "none")
  - stops, with their places, in full.

  This is enforced by the contract in
  `tests/api/acceptance/trips/schemas/trip-public.json`.

## Where things live

| File | Contents |
| --- | --- |
| `models.py` | the tables above, as SQLAlchemy models |
| `views.py` | response shapes, map-link builders, and the owner/redacted transformation (pure; unit tested) |
| `api.py` | endpoints; `_full_trip` eager-loads the whole tree, places included |
| `alembic.ini`, `migrations/` | this sub-app's migration chain ([migrations.md](migrations.md)) |


Endpoints for creating places, stops, stays and bookings don't exist yet. For now, trips
only get them through the seed (`scripts/api/seed/trips.py`).
