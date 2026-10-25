"""Who can see which trips: the one place trip access is decided.

For now the trips are shared by a small group of trusted friends. Anyone signed in (anyone
with an account in the Clerk instance, which is invite-only) can see every trip in full; no
one else can see any, which the endpoints enforce by requiring a token. Per-trip sharing
(trip members and invites) would replace these two functions, and nothing else would need to
change. See docs/trips.md.
"""

from sqlalchemy import ColumnElement, true

from api.trips.models import Trip


def visible_trips(user_id: str) -> ColumnElement[bool]:
    """A filter (for `select(Trip).where(...)`) matching the trips `user_id` may see."""
    return true()


def can_view(user_id: str, trip: Trip) -> bool:
    """Whether `user_id` may see `trip`."""
    return True
