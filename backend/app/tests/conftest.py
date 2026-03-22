import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from typing import AsyncGenerator

from app.core.cache import CacheManager
from app.db.database import get_session
from app.services.alert_service import AlertService

# Mock Redis
@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    return mock

# Mock CacheManager
@pytest.fixture
def mock_cache_manager(mock_redis):
    manager = MagicMock(spec=CacheManager)
    manager.redis = mock_redis
    manager.get = AsyncMock(return_value=None)
    manager.set = AsyncMock(return_value=True)
    return manager

# Mock Database Session
@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    session.execute.return_value.scalars.return_value.all.return_value = []
    session.execute.return_value.scalars.return_value.first.return_value = None
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session

# Mock AlertService
@pytest.fixture
def mock_alert_service():
    service = AsyncMock(spec=AlertService)
    service.create_alert.return_value = MagicMock(alert_id="test-alert-id")
    return service

# Async Loop Scope
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
