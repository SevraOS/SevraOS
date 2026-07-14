import pytest
import fakeredis.aioredis
from eventbus.client import RedisClientManager


@pytest.fixture
async def fake_redis():
    """
    Provides a fresh FakeRedis async instance for every test.
    """
    r = fakeredis.aioredis.FakeRedis()
    yield r
    await r.flushall()
    await r.aclose()


@pytest.fixture(autouse=True)
def mock_redis_client(fake_redis, monkeypatch):
    """
    Inject fakeredis into RedisClientManager so every test gets
    an isolated, in-memory Redis without a real server.
    """
    monkeypatch.setattr(RedisClientManager, "get_client", lambda: fake_redis)
    monkeypatch.setattr(RedisClientManager, "is_healthy", staticmethod(lambda: True))
    return fake_redis
