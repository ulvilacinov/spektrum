from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_ai_provider, get_db
from app.core.config import Settings, get_settings
from app.db import models  # noqa: F401
from app.db.base import Base
from app.main import create_app
from tests.fake_ai import FakeAIProvider


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
def upload_dir(tmp_path: Path) -> Path:
    path = tmp_path / "uploads"
    path.mkdir()
    return path


@pytest.fixture
def settings(upload_dir: Path) -> Settings:
    return get_settings().model_copy(
        update={
            "upload_dir": upload_dir,
            "max_upload_size_mb": 1,
            "ai_max_pages_per_request": 5,
            "ai_max_concurrency": 4,
            "gemini_api_key": None,
        }
    )


@pytest.fixture
def fake_ai() -> FakeAIProvider:
    return FakeAIProvider()


@pytest.fixture
def client(
    sqlite_session: Session, settings: Settings, fake_ai: FakeAIProvider
) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: sqlite_session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_ai_provider] = lambda: fake_ai
    with TestClient(app) as test_client:
        yield test_client
