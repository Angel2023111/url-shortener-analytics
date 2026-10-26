import pytest
from sqlalchemy.exc import OperationalError

from sqlalchemy.exc import OperationalError, InterfaceError

from app.tasks import refresh_url_analytics


def test_analytics_task_retry_configuration():
    assert refresh_url_analytics.max_retries == 3

    retry_for = refresh_url_analytics.autoretry_for
    assert OperationalError in retry_for
    assert InterfaceError in retry_for


def test_missing_short_url_returns_not_found(monkeypatch):
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def scalar(self, query):
            return None

    monkeypatch.setattr(
        "app.tasks.SessionLocal",
        lambda: FakeSession(),
    )

    result = refresh_url_analytics.run("missing-code")

    assert result == {
        "found": False,
        "short_code": "missing-code",
        "message": "Short URL not found",
    }


def test_transient_database_error_triggers_retry(monkeypatch):
    error = OperationalError(
        "SELECT 1",
        {},
        Exception("temporary connection failure"),
    )

    def fail_to_connect():
        raise error

    retry_calls = []

    def fake_retry(*, exc, **kwargs):
        retry_calls.append((exc, kwargs))
        raise RuntimeError("Retry requested")

    monkeypatch.setattr(
        "app.tasks.SessionLocal",
        fail_to_connect,
    )
    monkeypatch.setattr(
        refresh_url_analytics,
        "retry",
        fake_retry,
    )

    import pytest

    with pytest.raises(RuntimeError, match="Retry requested"):
        refresh_url_analytics.run("test-code")

    assert len(retry_calls) == 1
    assert retry_calls[0][0] is error
    assert "countdown" in retry_calls[0][1]