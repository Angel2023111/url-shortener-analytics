from unittest.mock import Mock

from app.celery_app import celery_app


def test_task_status_pending(client, monkeypatch):
    fake_task = Mock()
    fake_task.id = "task-pending-123"
    fake_task.state = "PENDING"

    monkeypatch.setattr(
        celery_app,
        "AsyncResult",
        lambda task_id: fake_task,
    )

    response = client.get("/api/tasks/task-pending-123")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "task-pending-123",
        "status": "PENDING",
    }


def test_task_status_success(client, monkeypatch):
    fake_task = Mock()
    fake_task.id = "task-success-123"
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

    response = client.get("/api/tasks/task-success-123")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "task-success-123",
        "status": "SUCCESS",
        "result": {
            "found": True,
            "short_code": "abc1234",
            "total_clicks": 5,
        },
    }


def test_task_status_failure(client, monkeypatch):
    fake_task = Mock()
    fake_task.id = "task-failure-123"
    fake_task.state = "FAILURE"

    monkeypatch.setattr(
        celery_app,
        "AsyncResult",
        lambda task_id: fake_task,
    )

    response = client.get("/api/tasks/task-failure-123")

    assert response.status_code == 200
    assert response.json() == {
        "task_id": "task-failure-123",
        "status": "FAILURE",
        "error": "Background task failed",
    }

def test_task_status_requires_api_key(client):
    client.headers.pop("X-API-Key")

    response = client.get("/api/tasks/task-pending-123")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"