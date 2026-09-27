from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_db
from app.db import models  # noqa: F401
from app.db.base import Base
from app.main import create_app


@pytest.fixture
def sqlite_session() -> Iterator[Session]:
    """In-memory SQLite for fast, DB-server-free unit tests of mappings and routes."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},  # TestClient runs handlers in a worker thread
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(sqlite_session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: sqlite_session
    with TestClient(app) as test_client:
        yield test_client
