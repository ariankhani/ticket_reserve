"""
Test configuration and fixtures for the ticket booking system.
"""
import os
from typing import Generator

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.db import Base, get_db
from app.main import app

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///./test_ticket.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def fake_redis():
    """Create a fake Redis client with lock support."""
    from unittest.mock import Mock
    redis = fakeredis.FakeRedis(decode_responses=True)
    
    # Track active locks for testing blocking behavior
    active_locks = set()
    
    def mock_lock(name, timeout=10, blocking_timeout=None):
        mock_lock_obj = Mock()
        
        def acquire_side_effect(blocking=False, blocking_timeout=None):
            if name in active_locks:
                return False  # Lock is already held
            active_locks.add(name)
            return True
        
        def release_side_effect():
            active_locks.discard(name)
            return None
        
        def enter_side_effect(*args, **kwargs):
            # Acquire the lock on context enter
            acquire_side_effect()
            return mock_lock_obj

        def exit_side_effect(*args, **kwargs):
            # release on context exit
            active_locks.discard(name)
            return None

        mock_lock_obj.acquire.side_effect = acquire_side_effect
        mock_lock_obj.release.side_effect = release_side_effect
        # use Mock objects for context manager methods so they accept the implicit self
        from unittest.mock import Mock as _Mock
        mock_lock_obj.__enter__ = _Mock(side_effect=enter_side_effect)
        mock_lock_obj.__exit__ = _Mock(side_effect=exit_side_effect)
        
        return mock_lock_obj
    
    redis.lock = mock_lock
    return redis


@pytest.fixture(scope="function")
def redis_client(fake_redis, monkeypatch):
    """Mock the Redis client used in the application."""
    def mock_get_redis_client():
        return fake_redis
    
    # Mock the get_redis_client function
    import app.services.bookings
    monkeypatch.setattr(app.services.bookings, "get_redis_client", mock_get_redis_client)
    
    return fake_redis


# Set test environment
os.environ["REDIS_URL"] = "redis://fake:6379/0"
