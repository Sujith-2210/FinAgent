"""
Rate Limiting Middleware
Enforces request limits based on IP or User ID using Redis.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import status
import time
from loguru import logger
from typing import Optional

from app.core.cache import cache_manager

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request rates.
    
    Limits:
    - Anonymous: 100 req/min
    - Authenticated: 500 req/min
    """
    
    async def dispatch(self, request: Request, call_next):
        if not cache_manager.is_healthy:
            # Fail open if cache is down
            return await call_next(request)
            
        # Identify client
        client_ip = request.client.host
        user_id = request.headers.get("X-User-ID") # Assumes gateway/auth sets this
        
        # Determine limit
        limit = 100 # Default/Anonymous
        window = 60 # 1 minute
        key_prefix = f"ratelimit:{client_ip}"
        
        if user_id:
            limit = 500
            key_prefix = f"ratelimit:user:{user_id}"
            
        # Current window key
        current_minute = int(time.time() // 60)
        key = f"{key_prefix}:{current_minute}"
        
        try:
            # Increment count
            # Use Redis INCR, which is atomic
            # We need raw redis access for this pattern usually, 
            # but CacheManager exposes abstractions. 
            # Let's use get/set with a small race condition window for now 
            # or extend CacheManager if needed. 
            # Ideally CacheManager should expose a 'increment' method.
            # For now, we will use the raw redis client from manager if available.
            
            if cache_manager.redis:
                pipeline = cache_manager.redis.pipeline()
                pipeline.incr(key)
                pipeline.expire(key, window + 10) # Expire after window + buffer
                result = await pipeline.execute()
                request_count = result[0]
            else:
                # Fallback if raw redis not accessible (shouldn't happen given is_healthy check)
                request_count = 1 
            
            # Check limit
            if request_count > limit:
                logger.warning(f"Rate limit exceeded for {key_prefix}: {request_count}/{limit}")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Too Many Requests",
                        "message": f"Rate limit exceeded. Try again in {window} seconds."
                    },
                    headers={"Retry-After": str(window)}
                )
                
        except Exception as e:
            logger.error(f"Rate limit error: {e}")
            # Fail open on error
            
        response = await call_next(request)
        return response
