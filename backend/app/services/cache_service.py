"""
Cache Service Layer
Provides high-level caching utilities and decorators.
"""

from typing import Any, Optional, Callable
from functools import wraps
import json
import hashlib
from loguru import logger
from app.core.cache import cache_manager

class CacheService:
    """
    Service for managing application-specific caching strategies.
    Wraps the low-level CacheManager.
    """
    
    @staticmethod
    def cached(ttl_seconds: int = 300, key_prefix: str = ""):
        """
        Decorator to cache async function results.
        
        Args:
            ttl_seconds: Time to live in seconds
            key_prefix: Prefix for the cache key
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                # 1. Use provided prefix or function name
                prefix = key_prefix or func.__name__
                
                # 2. Serialize args and kwargs to create a unique signature
                # Note: This is a simple implementation. Complex objects need custom serialization.
                try:
                    arg_str = json.dumps(args, default=str)
                    kwarg_str = json.dumps(kwargs, default=str, sort_keys=True)
                    signature = f"{arg_str}-{kwarg_str}"
                    sig_hash = hashlib.sha256(signature.encode()).hexdigest()
                    cache_key = f"{prefix}:{sig_hash}"
                except Exception as e:
                    logger.warning(f"Failed to generate cache key for {func.__name__}: {e}")
                    return await func(*args, **kwargs)
                
                # 3. Try execution
                try:
                    # Check cache
                    cached_value = await cache_manager.get(cache_key)
                    if cached_value:
                        logger.debug(f"Cache HIT for {cache_key}")
                        return cached_value
                    
                    # Execute function
                    result = await func(*args, **kwargs)
                    
                    # Cache result
                    if result is not None:
                        await cache_manager.set(cache_key, result, ttl=ttl_seconds)
                        logger.debug(f"Cache MISS - Set {cache_key}")
                        
                    return result
                except Exception as e:
                    logger.error(f"Caching error in {func.__name__}: {e}")
                    # Fallback to direct execution
                    return await func(*args, **kwargs)
                    
            return wrapper
        return decorator

    @staticmethod
    async def get_market_data(symbol: str) -> Optional[dict]:
        """Retrieve market data from cache."""
        return await cache_manager.get(f"market:{symbol}")

    @staticmethod
    async def set_market_data(symbol: str, data: dict, ttl: int = 60):
        """Cache market data."""
        await cache_manager.set(f"market:{symbol}", data, ttl=ttl)

    @staticmethod
    async def get_llm_cache(prompt: str, model: str) -> Optional[str]:
        """Retrieve LLM response from cache."""
        key = f"llm:{model}:{hashlib.sha256(prompt.encode()).hexdigest()}"
        return await cache_manager.get(key)
        
    @staticmethod
    async def set_llm_cache(prompt: str, model: str, response: str, ttl: int = 3600):
        """Cache LLM response."""
        key = f"llm:{model}:{hashlib.sha256(prompt.encode()).hexdigest()}"
        await cache_manager.set(key, response, ttl=ttl)

# Singleton
cache_service = CacheService()
