import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "postgresql://u:p@ep-x.eu-central-1.aws.neon.tech/vocab?sslmode=require",
            "postgresql+psycopg://u:p@ep-x.eu-central-1.aws.neon.tech/vocab?sslmode=require",
        ),
        ("postgres://u:p@db:5432/vocab", "postgresql+psycopg://u:p@db:5432/vocab"),
        (
            "postgresql+psycopg://u:p@127.0.0.1:5432/vocab",
            "postgresql+psycopg://u:p@127.0.0.1:5432/vocab",
        ),
        ("sqlite+pysqlite:///:memory:", "sqlite+pysqlite:///:memory:"),
    ],
)
def test_database_url_gets_the_psycopg_driver(url: str, expected: str) -> None:
    assert Settings(database_url=url).database_url == expected
