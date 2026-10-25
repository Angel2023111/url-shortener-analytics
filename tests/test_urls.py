

import os


from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.main import app
from app.models import URL



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

