
import pytest
from fastapi import HTTPException, Response

import app.rate_limit as rate_limit
from app.api_key_models import APIKey


def make_api_key(key_id: int) -> APIKey:
    return APIKey(
        id=key_id,
        key_hash=f"{key_id:064x}",
        name=f"test-key-{key_id}",
        is_active=True,
    )


def test_rate_limits_are_independent_per_api_key(monkeypatch):
    monkeypatch.setattr(rate_limit, "RATE_LIMIT", 2)
    monkeypatch.setattr(rate_limit, "WINDOW_SECONDS", 60)
    monkeypatch.setattr(rate_limit.time, "time", lambda: 120)

    counters = {}
    redis_keys = []

    def fake_eval(script, num_keys, key, window_seconds):
        redis_keys.append(key)
        counters[key] = counters.get(key, 0) + 1
        return counters[key]

    monkeypatch.setattr(rate_limit.redis_client, "eval", fake_eval)

    key_a = make_api_key(101)
    key_b = make_api_key(202)

    # Key A uses its first request.
    response_a = Response()
    rate_limit.rate_limit_url_creation(response_a, key_a)

    # Key A uses its second request.
    response_a = Response()
    rate_limit.rate_limit_url_creation(response_a, key_a)

    # Key B still gets its own quota.
    response_b = Response()
    rate_limit.rate_limit_url_creation(response_b, key_b)

    assert response_b.headers["X-RateLimit-Remaining"] == "1"
    assert len(set(redis_keys)) == 2
    assert any(":101:" in key for key in redis_keys)
    assert any(":202:" in key for key in redis_keys)


def test_rate_limit_returns_429_after_quota_is_exceeded(monkeypatch):
    monkeypatch.setattr(rate_limit, "RATE_LIMIT", 1)
    monkeypatch.setattr(rate_limit, "WINDOW_SECONDS", 60)
    monkeypatch.setattr(rate_limit.time, "time", lambda: 120)

    counter = {"count": 0}

    def fake_eval(script, num_keys, key, window_seconds):
        counter["count"] += 1
        return counter["count"]

    monkeypatch.setattr(rate_limit.redis_client, "eval", fake_eval)

    key = make_api_key(303)

    # First request is allowed.
    response = Response()
    rate_limit.rate_limit_url_creation(response, key)

    # Second request exceeds the configured limit.
    with pytest.raises(HTTPException) as exc_info:
        rate_limit.rate_limit_url_creation(Response(), key)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["Retry-After"] == "60"
    assert exc_info.value.headers["X-RateLimit-Remaining"] == "0"
