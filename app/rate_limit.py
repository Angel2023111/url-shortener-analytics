
import os
import time

from fastapi import HTTPException, Request, Response
from redis.exceptions import RedisError

from app.cache import redis_client


RATE_LIMIT = int(os.getenv("URL_CREATE_RATE_LIMIT", "10"))
WINDOW_SECONDS = int(
    os.getenv("URL_CREATE_WINDOW_SECONDS", "60")
)

# Increment the counter and set its TTL atomically.
INCREMENT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


def rate_limit_url_creation(
    request: Request,
    response: Response,
) -> None:
    # Identify the client. This is suitable for local development.
    client_ip = (
        request.client.host
        if request.client is not None
        else "unknown"
    )

    now = int(time.time())
    window_id = now // WINDOW_SECONDS
    seconds_until_reset = (
        WINDOW_SECONDS - (now % WINDOW_SECONDS)
    )

    key = f"rate_limit:create_url:{client_ip}:{window_id}"

    try:
        current_count = int(
            redis_client.eval(
                INCREMENT_SCRIPT,
                1,
                key,
                WINDOW_SECONDS,
            )
        )
    except RedisError:
        # Fail open: keep URL creation available if Redis is down.
        # This temporarily means the rate limit cannot be enforced.
        return

    remaining = max(0, RATE_LIMIT - current_count)

    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
    response.headers["X-RateLimit-Remaining"] = str(remaining)

    if current_count > RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many URL creation requests. Try again later.",
            headers={
                "Retry-After": str(seconds_until_reset),
                "X-RateLimit-Limit": str(RATE_LIMIT),
                "X-RateLimit-Remaining": "0",
            },
        )
