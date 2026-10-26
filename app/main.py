import os
import secrets
import string
from collections.abc import Generator

from fastapi import Depends, FastAPI, HTTPException, status, Query
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import URL
from app.schemas import URLCreate, URLResponse

from datetime import datetime, timezone
from datetime import timedelta
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.click_models import Click

from sqlalchemy import func, select

from app.cache import (
    get_cached_url,
    set_cached_url,
    invalidate_cached_url,
)

from app.rate_limit import rate_limit_url_creation

from app.celery_app import celery_app
from app.tasks import refresh_url_analytics

app = FastAPI(
    title="URL Shortener & Analytics API",
    description="""
    API for creating short URLs, redirecting visitors, and tracking clicks.

    ## Features
    - Create short URLs with input validation and rate limiting.
    - Redirect visitors to original URLs.
    - Track total and daily click analytics.
    - Cache redirect lookups using Redis.
    - Refresh analytics asynchronously using Celery.
    """,
    version="1.0.0",
    contact={
        "name": "API Support",
    },
)

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
ALPHABET = string.ascii_letters + string.digits


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_short_code(length: int = 7) -> str:
    return "".join(
        secrets.choice(ALPHABET) for _ in range(length)
    )


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "url-shortener"}


@app.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "connected"}


@app.post(
    "/api/urls",
    response_model=URLResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_url_creation)],
)
def create_url(
    request: URLCreate,
    db: Session = Depends(get_db),
):
    for _ in range(3):
        short_code = generate_short_code()

        url = URL(
            short_code=short_code,
            original_url=str(request.original_url),
            expires_at=request.expires_at,
        )

        try:
            db.add(url)
            db.commit()
            db.refresh(url)

            return URLResponse(
                id=url.id,
                short_code=url.short_code,
                original_url=url.original_url,
                short_url=f"{BASE_URL.rstrip('/')}/{url.short_code}",
                created_at=url.created_at,
                expires_at=url.expires_at,
            )

        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Database constraint violation.",
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Could not generate a unique short code. Please retry.",
    )


@app.post("/api/urls/{short_code}/analytics/refresh", status_code=202)
def enqueue_analytics_refresh(short_code: str):
    task = refresh_url_analytics.delay(short_code)

    return {
        "task_id": task.id,
        "status": "PENDING",
    }


@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    task = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task.id,
        "status": task.state,
    }

    if task.state == "SUCCESS":
        response["result"] = task.result
    elif task.state == "FAILURE":
        response["error"] = "Background task failed"

    return response



@app.get("/{short_code}")
def redirect_url(short_code: str, db: Session = Depends(get_db)):
    # 1. Try Redis first.
    cached_data = get_cached_url(short_code)

    if cached_data is not None:
        try:
            url_id = cached_data["url_id"]
            original_url = cached_data["original_url"]

            expires_at_raw = cached_data["expires_at"]
            expires_at = (
                datetime.fromisoformat(expires_at_raw)
                if expires_at_raw is not None
                else None
            )
        except (KeyError, ValueError, TypeError):
            # Invalid cache data: discard it and use PostgreSQL.
            invalidate_cached_url(short_code)
            cached_data = None

    # 2. Cache miss or Redis failure: query PostgreSQL.
    if cached_data is None:
        statement = select(URL).where(
            URL.short_code == short_code
        )
        url = db.scalar(statement)

        if url is None:
            raise HTTPException(
                status_code=404,
                detail="Short URL not found",
            )

        url_id = url.id
        original_url = url.original_url
        expires_at = url.expires_at

    # 3. Check expiration on BOTH cache hits and cache misses.
    now = datetime.now(timezone.utc)

    if expires_at is not None and expires_at <= now:
        invalidate_cached_url(short_code)
        raise HTTPException(
            status_code=410,
            detail="This short URL has expired",
        )

    # 4. Cache valid database results.
    if cached_data is None:
        set_cached_url(
            short_code,
            {
                "url_id": url_id,
                "original_url": original_url,
                "expires_at": (
                    expires_at.isoformat()
                    if expires_at is not None
                    else None
                ),
            },
        )

    # 5. Record EVERY successful redirect in PostgreSQL.
    click = Click(url_id=url_id)
    db.add(click)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    # 6. Return the original redirect response.
    return RedirectResponse(
        url=original_url,
        status_code=307,
    )



@app.get("/api/urls/{short_code}/analytics")
def get_url_analytics(
    short_code: str,
    db: Session = Depends(get_db),
):
    url = db.scalar(
        select(URL).where(URL.short_code == short_code)
    )

    if url is None:
        raise HTTPException(
            status_code=404,
            detail="Short URL not found",
        )

    total_clicks = db.scalar(
        select(func.count(Click.id))
        .where(Click.url_id == url.id)
    )

    return {
        "short_code": url.short_code,
        "original_url": url.original_url,
        "created_at": url.created_at,
        "expires_at": url.expires_at,
        "total_clicks": total_clicks,
    }


@app.get("/api/urls/{short_code}/analytics/daily")
def get_daily_analytics(
    short_code: str,
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    url = db.scalar(
        select(URL).where(URL.short_code == short_code)
    )

    if url is None:
        raise HTTPException(
            status_code=404,
            detail="Short URL not found",
        )

    # Group clicks by UTC calendar day.
    click_day = func.date_trunc(
        "day",
        func.timezone("UTC", Click.clicked_at),
    ).label("day")

    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    statement = (
        select(click_day, func.count(Click.id).label("clicks"))
        .where(
            Click.url_id == url.id,
            Click.clicked_at >= cutoff,
        )
        .group_by(click_day)
        .order_by(click_day)
    )

    rows = db.execute(statement).all()

    return {
        "short_code": url.short_code,
        "period_days": days,
        "daily_clicks": [
            {
                "date": row.day.date().isoformat(),
                "clicks": row.clicks,
            }
            for row in rows
        ],
    }

