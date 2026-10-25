import pytest

from scripts.api.seed import is_local_database


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@localhost:5432/db",
        "postgresql://u:p@127.0.0.1/db",
        "postgresql://u:p@db:5432/houseplant",
    ],
)
def test_is_local_database_accepts_local_hosts(url):
    assert is_local_database(url)


def test_is_local_database_rejects_remote_hosts():
    assert not is_local_database("postgresql://u:p@dpg-abc123.render.com:5432/prod")
