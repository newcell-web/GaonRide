import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import backend.models  # ensure all ORM classes are registered on Base before create_all
from backend.database import Base, get_db
from backend.main import app

# In-memory SQLite engine for tests.
# StaticPool ensures all connections from the pool share the same in-memory DB,
# so create_all and the test sessions see the same tables.
@pytest.fixture(scope="function")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(test_engine):
    # Use autoflush=True to match production SessionLocal behaviour
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function")
def client(test_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=test_engine)
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
