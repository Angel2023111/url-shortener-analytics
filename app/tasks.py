
from celery import shared_task
from sqlalchemy import func, select
from sqlalchemy.exc import InterfaceError, OperationalError

from app.click_models import Click
from app.database import SessionLocal
from app.models import URL


@shared_task(
    name="app.tasks.refresh_url_analytics",
    bind=True,
    max_retries=3,
    autoretry_for=(OperationalError, InterfaceError),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def refresh_url_analytics(self, short_code: str) -> dict:
    """Calculate a URL's click analytics in a background worker."""
    with SessionLocal() as db:
        url = db.scalar(
            select(URL).where(URL.short_code == short_code)
        )

        if url is None:
            return {
                "found": False,
                "short_code": short_code,
                "message": "Short URL not found",
            }

        total_clicks = db.scalar(
            select(func.count(Click.id)).where(
                Click.url_id == url.id
            )
        )

        return {
            "found": True,
            "short_code": url.short_code,
            "original_url": url.original_url,
            "total_clicks": int(total_clicks or 0),
            "created_at": url.created_at.isoformat(),
            "expires_at": (
                url.expires_at.isoformat()
                if url.expires_at is not None
                else None
            ),
        }
