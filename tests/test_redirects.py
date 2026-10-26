
import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app import main as main_module
from app.models import URL
from app.click_models import Click


def insert_test_url(original_url, expires_at=None):
    engine = create_engine(os.environ["TEST_DATABASE_URL"])

    try:
        with Session(engine) as db:
            url = URL(
                short_code=uuid.uuid4().hex[:7],
                original_url=original_url,
                expires_at=expires_at,
            )
            db.add(url)
            db.commit()
            db.refresh(url)

            return url.short_code, url.id
    finally:
        engine.dispose()


def test_redirects_valid_url(client, monkeypatch):
    short_code, url_id = insert_test_url("https://example.com/target")

    # Avoid depending on Redis state during this test.
    monkeypatch.setattr(
        main_module, "get_cached_url", lambda code: None
    )
    monkeypatch.setattr(
        main_module, "set_cached_url", lambda code, data: None
    )
    monkeypatch.setattr(
        main_module, "invalidate_cached_url", lambda code: None
    )

    response = client.get(
        f"/{short_code}",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/target"

    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    try:
        with Session(engine) as db:
            click_count = len(
                db.scalars(
                    select(Click).where(Click.url_id == url_id)
                ).all()
            )
            assert click_count == 1
    finally:
        engine.dispose()


def test_redirect_unknown_code_returns_404(client, monkeypatch):
    monkeypatch.setattr(
        main_module, "get_cached_url", lambda code: None
    )
    monkeypatch.setattr(
        main_module, "invalidate_cached_url", lambda code: None
    )

    response = client.get(
        "/unknown",
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Short URL not found"


def test_redirect_expired_url_returns_410(client, monkeypatch):
    expired_at = datetime.now(timezone.utc) - timedelta(days=1)
    short_code, _ = insert_test_url(
        "https://example.com/expired",
        expires_at=expired_at,
    )

    monkeypatch.setattr(
        main_module, "get_cached_url", lambda code: None
    )
    monkeypatch.setattr(
        main_module, "set_cached_url", lambda code, data: None
    )
    monkeypatch.setattr(
        main_module, "invalidate_cached_url", lambda code: None
    )

    response = client.get(
        f"/{short_code}",
        follow_redirects=False,
    )

    assert response.status_code == 410
    assert response.json()["detail"] == "This short URL has expired"


def test_redirects_url_with_future_expiration(client, monkeypatch):
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    short_code, _ = insert_test_url(
        "https://example.com/future",
        expires_at=expires_at,
    )

    monkeypatch.setattr(
        main_module, "get_cached_url", lambda code: None
    )
    monkeypatch.setattr(
        main_module, "set_cached_url", lambda code, data: None
    )
    monkeypatch.setattr(
        main_module, "invalidate_cached_url", lambda code: None
    )

    response = client.get(
        f"/{short_code}",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/future"


def test_cached_expired_url_returns_410(client, monkeypatch):
    expired_at = datetime.now(timezone.utc) - timedelta(days=1)
    short_code, url_id = insert_test_url(
        "https://example.com/cached-expired",
        expires_at=expired_at,
    )

    # Simulate Redis returning a cached URL that has expired.
    monkeypatch.setattr(
        main_module,
        "get_cached_url",
        lambda code: {
            "url_id": url_id,
            "original_url": "https://example.com/cached-expired",
            "expires_at": expired_at.isoformat(),
        },
    )
    monkeypatch.setattr(
        main_module, "invalidate_cached_url", lambda code: None
    )

    response = client.get(
        f"/{short_code}",
        follow_redirects=False,
    )

    assert response.status_code == 410
    assert response.json()["detail"] == "This short URL has expired"

