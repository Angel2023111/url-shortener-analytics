
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import app as fastapi_app, get_db
import app.models
import app.click_models
import app.api_key_models

from app.api_key_models import APIKey
from app.api_keys import generate_api_key, hash_api_key
from app.rate_limit import rate_limit_url_creation


@pytest.fixture
def client():
    database_url = os.environ["TEST_DATABASE_URL"]
    test_engine = create_engine(database_url)

    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=test_engine)

    raw_key = generate_api_key()

    with TestingSessionLocal() as db:
        db.add(
            APIKey(
                key_hash=hash_api_key(raw_key),
                name="pytest-client",
                is_active=True,
            )
        )
        db.commit()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    fastapi_app.dependency_overrides[rate_limit_url_creation] = lambda: None
    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        # Keep the test key available to tests through a fixture.
        test_client.headers.update({"X-API-Key": raw_key})
        yield test_client

    fastapi_app.dependency_overrides.clear()
    test_engine.dispose()
