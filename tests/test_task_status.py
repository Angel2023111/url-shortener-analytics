from unittest.mock import Mock

from app.celery_app import celery_app

from app.api_key_models import APIKey
from app.task_ownership_models import TaskOwnership

import uuid



def test_task_status_pending(client, monkeypatch):
    fake_task = Mock()
    fake_task.id = f"task-pending-{uuid.uuid4()}"
    fake_task.state = "PENDING"

    monkeypatch.setattr(
        celery_app,
        "AsyncResult",
        lambda task_id: fake_task,
    )
    with client.app.state.TestingSessionLocal() as db:
        api_key_id = client.app.state.TestAPIKeyID

        db.add(
            TaskOwnership(
                task_id=fake_task.id,
                api_key_id=api_key_id,
            )
        )
        db.commit()



    response = client.get(f"/api/tasks/{fake_task.id}")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": fake_task.id,
        "status": "PENDING",
    }


def test_task_status_success(client, monkeypatch):
    fake_task = Mock()
    fake_task.id = f"task-success-{uuid.uuid4()}"
    fake_task.state = "SUCCESS"
    fake_task.result = {
        "found": True,
        "short_code": "abc1234",
        "total_clicks": 5,
    }

    monkeypatch.setattr(
        celery_app,
        "AsyncResult",
        lambda task_id: fake_task,
    )

    with client.app.state.TestingSessionLocal() as db:
        api_key_id = client.app.state.TestAPIKeyID

        db.add(
            TaskOwnership(
                task_id=fake_task.id,
                api_key_id=api_key_id,
            )
        )
        db.commit()


    response = client.get(f"/api/tasks/{fake_task.id}")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": fake_task.id,
        "status": "SUCCESS",
        "result": {
            "found": True,
            "short_code": "abc1234",
            "total_clicks": 5,
        },
    }


def test_task_status_failure(client, monkeypatch):
    fake_task = Mock()
    fake_task.id = f"task-failure-{uuid.uuid4()}"
    fake_task.state = "FAILURE"

    monkeypatch.setattr(
        celery_app,
        "AsyncResult",
        lambda task_id: fake_task,
    )

    with client.app.state.TestingSessionLocal() as db:
        api_key_id = client.app.state.TestAPIKeyID

        db.add(
            TaskOwnership(
                task_id=fake_task.id,
                api_key_id=api_key_id,
            )
        )
        db.commit()

    response = client.get(f"/api/tasks/{fake_task.id}")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": fake_task.id,
        "status": "FAILURE",
        "error": "Background task failed",
    }

def test_task_status_requires_api_key(client):
    client.headers.pop("X-API-Key")

    response = client.get("/api/tasks/task-pending-123")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"
