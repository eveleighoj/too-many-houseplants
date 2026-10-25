import pytest

from api.common.db import sqlalchemy_url


@pytest.mark.parametrize(
    "url",
    ["postgres://u:p@host:5432/db", "postgresql://u:p@host:5432/db"],
)
def test_sqlalchemy_url_points_plain_postgres_urls_at_psycopg(url):
    assert sqlalchemy_url(url) == "postgresql+psycopg://u:p@host:5432/db"


def test_sqlalchemy_url_leaves_explicit_driver_alone():
    url = "postgresql+psycopg://u:p@host:5432/db"

    assert sqlalchemy_url(url) == url
