"""
Redis Cache Manager
Core infrastructure for application-wide caching.
"""

import json
from typing import Any, Optional, Union, List
import redis.asyncio as aioredis
from loguru import logger
import os
from datetime import timedelta

class CacheManager:
    """
    Async Redis Cache Manager.
    
    Handles low-level Redis operations with error handling and serialization.
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[aioredis.Redis] = None
        self._is_connected = False
        
    async def connect(self):
        """Establish Redis connection."""
        try:
            self.redis = aioredis.from_url(
                self.redis_url, 
                encoding="utf-8", 
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            await self.redis.ping()
            self._is_connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching will be disabled.")
            self._is_connected = False
            
    async def disconnect(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            self._is_connected = False
            logger.info("Disconnected from Redis")
            
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache."""
        if not self._is_connected or not self.redis:
            return None
            
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache GET error for {key}: {e}")
            return None
            
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Union[int, timedelta] = 300
    ) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Data to cache (must be JSON serializable)
            ttl: Time to live in seconds or timedelta (default: 5 minutes)
        """
        if not self._is_connected or not self.redis:
            return False
            
        try:
            serialized = json.dumps(value)
            
            # Handle timedelta
            if isinstance(ttl, timedelta):
                ttl_seconds = int(ttl.total_seconds())
            else:
                ttl_seconds = ttl
                
            await self.redis.set(key, serialized, ex=ttl_seconds)
            return True
        except TypeError as e:
            logger.error(f"Serialization error for key {key}: {e}")
            return False
        except Exception as e:
            logger.error(f"Cache SET error for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._is_connected or not self.redis:
            return False
            
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache DELETE error for {key}: {e}")
            return False
            
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._is_connected or not self.redis:
            return False
            
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache EXISTS error for {key}: {e}")
            return False
            
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern (e.g., 'market:*')."""
        if not self._is_connected or not self.redis:
            return 0
            
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} keys matching '{pattern}'")
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"Cache CLEAR error for {pattern}: {e}")
            return 0

    @property
    def is_healthy(self) -> bool:
        """Check if cache is operational."""
        return self._is_connected

# Singleton instance
cache_manager = CacheManager()
