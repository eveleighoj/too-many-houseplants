from sqlalchemy import select

from api.trips.access import can_view, visible_trips
from api.trips.models import Trip


def make_trip(owner_id: str) -> Trip:
    return Trip(owner_id=owner_id, title="Scotland")


def test_can_view_lets_any_signed_in_user_see_any_trip():
    assert can_view("user_owner", make_trip("user_owner"))
    assert can_view("user_friend", make_trip("user_owner"))


def test_visible_trips_does_not_restrict_by_owner():
    sql = str(select(Trip).where(visible_trips("user_friend")).compile())

    assert "owner_id" not in sql.split("WHERE", 1)[-1]
