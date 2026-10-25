
import os

from celery import Celery

celery_app = Celery(
    "url_shortener",
    broker=os.getenv(
        "CELERY_BROKER_URL",
        "redis://localhost:6379/1",
    ),
    backend=os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://localhost:6379/2",
    ),
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)
