
import json
import os

from redis import Redis
from redis.exceptions import RedisError


CACHE_TTL_SECONDS = int(
    os.getenv("URL_CACHE_TTL_SECONDS", "300")
)

redis_client = Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)


def get_cached_url(short_code: str) -> dict | None:
    """Return cached URL metadata, or None on a miss/error."""
    key = f"url:{short_code}"

    try:
        cached_value = redis_client.get(key)

        if cached_value is None:
            return None

        data = json.loads(cached_value)

        if (
            not isinstance(data, dict)
            or not isinstance(data.get("url_id"), int)
            or not isinstance(data.get("original_url"), str)
            or (
                data.get("expires_at") is not None
                and not isinstance(data.get("expires_at"), str)
            )
        ):
            redis_client.delete(key)
            return None

        return data

    except (RedisError, ValueError, TypeError):
        # Redis errors must not prevent a database fallback.
        return None


def set_cached_url(short_code: str, data: dict) -> None:
    """Cache URL metadata with a finite TTL."""
    try:
        redis_client.set(
            f"url:{short_code}",
            json.dumps(data),
            ex=CACHE_TTL_SECONDS,
        )
    except (RedisError, TypeError, ValueError):
        # Caching is optional; the database remains authoritative.
        pass


def invalidate_cached_url(short_code: str) -> None:
    """Remove a URL mapping from Redis."""
    try:
        redis_client.delete(f"url:{short_code}")
    except RedisError:
        # A failed invalidation must not crash the application.
        pass
