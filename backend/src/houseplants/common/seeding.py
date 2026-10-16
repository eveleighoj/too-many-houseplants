"""Fixed, readable ids for local seed data, so the same seeded row always has the same id.

    seed_id(kind, number) -> "0000000<kind>-0000-4000-8000-<number, 12 digits>"

e.g. trip 1 is 00000002-0000-4000-8000-000000000001. Each sub-app's seed picks its own kinds
(listed in docs/local-development.md#seed-data) and how it numbers rows.
"""

import uuid


def seed_id(kind: int, number: int) -> uuid.UUID:
    if not (0 < kind < 10**8 and 0 < number < 10**12):
        raise ValueError(f"seed id out of range: kind={kind}, number={number}")
    # Decimal digits are valid hex, so the id reads the same as the numbers that made it.
    return uuid.UUID(f"{kind:08d}-0000-4000-8000-{number:012d}")
