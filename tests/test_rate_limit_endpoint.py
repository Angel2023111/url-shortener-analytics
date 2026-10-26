
import app.rate_limit as rate_limit


def test_endpoint_enforces_independent_api_key_limits(
    client_with_rate_limit, monkeypatch
):
    client, raw_keys = client_with_rate_limit

    monkeypatch.setattr(rate_limit, "RATE_LIMIT", 1)
    monkeypatch.setattr(rate_limit, "WINDOW_SECONDS", 60)
    monkeypatch.setattr(rate_limit.time, "time", lambda: 120)

    counters = {}

    def fake_eval(script, num_keys, key, window_seconds):
        counters[key] = counters.get(key, 0) + 1
        return counters[key]

    monkeypatch.setattr(
        rate_limit.redis_client, "eval", fake_eval
    )

    body = {"original_url": "https://example.com"}

    # API key A's first request succeeds.
    response_a1 = client.post(
        "/api/urls",
        json=body,
        headers={"X-API-Key": raw_keys[0]},
    )
    assert response_a1.status_code == 201
    assert response_a1.headers["X-RateLimit-Remaining"] == "0"

    # API key A's second request exceeds its quota.
    response_a2 = client.post(
        "/api/urls",
        json=body,
        headers={"X-API-Key": raw_keys[0]},
    )
    assert response_a2.status_code == 429
    assert response_a2.headers["Retry-After"] == "60"

    # API key B still has its own quota.
    response_b1 = client.post(
        "/api/urls",
        json=body,
        headers={"X-API-Key": raw_keys[1]},
    )
    assert response_b1.status_code == 201
    assert response_b1.headers["X-RateLimit-Remaining"] == "0"

    # Two distinct Redis counters were used.
    assert len(counters) == 2
