"""
HELIOS OS + SEVRA AI
Tests - Cache Layer
"""

import pytest
from unittest.mock import patch, AsyncMock
from database.cache.manager import CacheManager

@pytest.mark.asyncio
async def test_cache_set_and_get():
    manager = CacheManager()
    
    with patch('database.cache.manager.RedisClientManager.get_client') as mock_get_client:
        mock_redis = AsyncMock()
        mock_get_client.return_value = mock_redis
        
        # Test Set
        await manager.set_latest_vital("pat-1", "hr", {"value": 80})
        mock_redis.set.assert_called_once()
        args = mock_redis.set.call_args
        assert "vital:latest:pat-1:hr" in args[0][0]
        assert b"80" in args[0][1].encode() # basic check payload contains data
        
        # Test Get
        mock_redis.get.return_value = '{"value": 80}'.encode()
        result = await manager.get_latest_vital("pat-1", "hr")
        mock_redis.get.assert_called_once()
        assert result == {"value": 80}

@pytest.mark.asyncio
async def test_cache_miss_returns_none():
    manager = CacheManager()
    
    with patch('database.cache.manager.RedisClientManager.get_client') as mock_get_client:
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_get_client.return_value = mock_redis
        
        result = await manager.get_patient_summary("unknown")
        assert result is None
