import os


from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.main import app
from app.models import URL

from datetime import datetime, timedelta, timezone

def test_create_url_rejects_invalid_url(client):
    response = client.post(
        "/api/urls",
        json={"original_url": "not-a-valid-url"},
    )

    assert response.status_code == 422


def test_create_url_persists_record(client):
    response = client.post(
        "/api/urls",
        json={"original_url": "https://example.com/path"},
    )

    assert response.status_code == 201

    data = response.json()
    assert data["short_code"]
    assert data["short_url"].endswith("/" + data["short_code"])
    assert data["original_url"] == "https://example.com/path"

    test_engine = create_engine(os.environ["TEST_DATABASE_URL"])
    try:
        with Session(test_engine) as db:
            saved_url = db.scalar(
                select(URL).where(URL.short_code == data["short_code"])
            )

            assert saved_url is not None
            assert saved_url.original_url == data["original_url"]
    finally:
        test_engine.dispose()


def test_create_url_with_future_expiration(client):
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)

    response = client.post(
        "/api/urls",
        json={
            "original_url": "https://example.com/expiring",
            "expires_at": expires_at.isoformat(),
        },
    )

    assert response.status_code == 201
    assert response.json()["expires_at"] is not None


def test_create_url_rejects_past_expiration(client):
    expires_at = datetime.now(timezone.utc) - timedelta(days=1)

    response = client.post(
        "/api/urls",
        json={
            "original_url": "https://example.com/expired",
            "expires_at": expires_at.isoformat(),
        },
    )

    assert response.status_code == 422


def test_create_url_rejects_expiration_without_timezone(client):
    response = client.post(
        "/api/urls",
        json={
            "original_url": "https://example.com/no-timezone",
            "expires_at": "2026-11-01T18:00:00",
        },
    )

    assert response.status_code == 422


