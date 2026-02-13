"""
Redis caching layer for CuanBot.
Gracefully degrades if Redis is unavailable — never crashes the app.
"""

import os
import json
import hashlib
from functools import wraps
from logger import get_logger

log = get_logger("cache")

# TTL presets (seconds)
TTL_MARKET_DATA = 300       # 5 minutes
TTL_ANALYSIS = 900          # 15 minutes
TTL_NEWS = 1800             # 30 minutes
TTL_LLM = 3600              # 1 hour
TTL_SCREENER = 600          # 10 minutes

_redis_client = None


def _get_redis():
    """Lazy-init Redis connection."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        _redis_client = redis.from_url(url, decode_responses=True, socket_timeout=2)
        _redis_client.ping()
        log.info(f"Redis connected: {url}")
        return _redis_client
    except Exception as e:
        log.warning(f"Redis unavailable, caching disabled: {e}")
        _redis_client = None
        return None


def cache_key(*parts) -> str:
    """Build a consistent cache key from parts."""
    raw = ":".join(str(p) for p in parts)
    return f"cuanbot:{raw}"


def get_cache(key: str):
    """Get value from cache. Returns None on miss or error."""
    r = _get_redis()
    if r is None:
        return None
    try:
        val = r.get(key)
        if val is not None:
            return json.loads(val)
    except Exception as e:
        log.warning(f"Cache read error: {e}")
    return None


def set_cache(key: str, value, ttl: int = TTL_ANALYSIS):
    """Set value in cache with TTL. Silently fails if Redis is down."""
    r = _get_redis()
    if r is None:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        log.warning(f"Cache write error: {e}")


def delete_cache(key: str):
    """Delete a cache key."""
    r = _get_redis()
    if r is None:
        return
    try:
        r.delete(key)
    except Exception:
        pass


def cached(prefix: str, ttl: int = TTL_ANALYSIS):
    """
    Decorator for caching function results.

    Usage:
        @cached("market_data", ttl=TTL_MARKET_DATA)
        def get_stock_data(symbol):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from function args
            key_parts = [prefix, func.__name__] + [str(a) for a in args]
            key_parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
            key = cache_key(*key_parts)

            # Try cache first
            result = get_cache(key)
            if result is not None:
                log.debug(f"Cache HIT: {key}")
                return result

            # Cache miss — execute function
            log.debug(f"Cache MISS: {key}")
            result = func(*args, **kwargs)

            # Only cache successful results (no error key)
            if isinstance(result, dict) and "error" not in result:
                set_cache(key, result, ttl)

            return result
        return wrapper
    return decorator
