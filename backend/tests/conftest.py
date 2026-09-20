import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ANTHROPIC_API_KEY", "fake-key-for-tests")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Import Base first, then all models to register their metadata
from app.database import Base, get_db, set_engine

import app.models.user          # noqa: F401
import app.models.account       # noqa: F401
import app.models.document      # noqa: F401
import app.models.transaction   # noqa: F401
import app.models.recurring     # noqa: F401
import app.models.budget        # noqa: F401
import app.models.goal          # noqa: F401
import app.models.insight       # noqa: F401
import app.models.summary       # noqa: F401
import app.models.chat          # noqa: F401

from app.services.llm_provider import FakeLLMProvider, get_llm_provider
from app.main import app

# StaticPool ensures ALL connections share ONE in-memory DB (critical for SQLite :memory:)
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
# Inject into app so lifespan's init_db() also uses this engine
set_engine(TEST_ENGINE)
# Create tables after all models are imported
Base.metadata.create_all(bind=TEST_ENGINE)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(scope="function")
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_llm():
        return FakeLLMProvider()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_llm_provider] = override_get_llm

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()
