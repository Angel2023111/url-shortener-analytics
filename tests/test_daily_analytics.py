
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import URL
from app.click_models import Click


def test_daily_analytics_returns_click_counts(client):
    engine = create_engine(os.environ["TEST_DATABASE_URL"])

    try:
        with Session(engine) as db:
            url = URL(
                short_code=uuid.uuid4().hex[:7],
                original_url="https://example.com/daily",
            )
            db.add(url)
            db.commit()
            db.refresh(url)

            # Create two clicks for today.
            db.add_all([
                Click(url_id=url.id, clicked_at=datetime.now(timezone.utc)),
                Click(url_id=url.id, clicked_at=datetime.now(timezone.utc)),
            ])
            db.commit()

            short_code = url.short_code

        response = client.get(
            f"/api/urls/{short_code}/analytics/daily?days=7"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["short_code"] == short_code
        assert data["period_days"] == 7
        assert len(data["daily_clicks"]) == 1
        assert data["daily_clicks"][0]["clicks"] == 2

    finally:
        engine.dispose()


def test_daily_analytics_rejects_invalid_days(client):
    response = client.get("/api/urls/anything/analytics/daily?days=0")
    assert response.status_code == 422
