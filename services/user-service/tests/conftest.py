import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from user_app.db.base import Base  # noqa: E402
from user_app.db import models  # noqa: F401, E402
from user_app.db.session import get_db  # noqa: E402
from user_app.main import app  # noqa: E402


def _database_url() -> str:
    for key in ("TEST_DATABASE_URL", "DATABASE_URL"):
        if url := os.getenv(key):
            return url
    return "postgresql+psycopg://eventradar:eventradar@127.0.0.1:5432/eventradar"


@pytest.fixture(scope="session")
def engine():
    url = _database_url()
    eng = create_engine(url, pool_pre_ping=True)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not available at {url}: {exc}")
    # Idempotent — never drop_all; tests roll back per transaction.
    Base.metadata.create_all(eng)
    yield eng


@pytest.fixture
def db_session(engine) -> Session:
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def api_client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
