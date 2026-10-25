
import os
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import URL
from app.click_models import Click


def create_url_with_clicks(click_count: int):
    engine = create_engine(os.environ["TEST_DATABASE_URL"])

    try:
        with Session(engine) as db:
            url = URL(
                short_code=uuid.uuid4().hex[:7],
                original_url="https://example.com/analytics",
            )
            db.add(url)
            db.commit()
            db.refresh(url)

            for _ in range(click_count):
                db.add(Click(url_id=url.id))

            db.commit()

            return url.short_code
    finally:
        engine.dispose()


def test_analytics_returns_correct_click_count(client):
    short_code = create_url_with_clicks(3)

    response = client.get(
        f"/api/urls/{short_code}/analytics"
    )

    assert response.status_code == 200

    data = response.json()
    assert data["short_code"] == short_code
    assert data["original_url"] == "https://example.com/analytics"
    assert data["total_clicks"] == 3


def test_analytics_unknown_code_returns_404(client):
    response = client.get(
        "/api/urls/unknown/analytics"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Short URL not found"
