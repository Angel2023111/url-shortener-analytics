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

app = FastAPI(
    title="URL Shortener API",
    description="A URL shortening and click analytics service.",
    version="0.2.0",
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
            print("DATABASE INTEGRITY ERROR:", exc.orig)
            raise HTTPException(
                status_code=500,
                detail="Database constraint violation.",
            ) from exc

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Could not generate a unique short code. Please retry.",
    )



@app.get("/{short_code}")
def redirect_url(
    short_code: str,
    db: Session = Depends(get_db),
):
    statement = select(URL).where(URL.short_code == short_code)
    url = db.scalar(statement)

    if url is None:
        raise HTTPException(
            status_code=404,
            detail="Short URL not found",
        )

    now = datetime.now(timezone.utc)

    if url.expires_at is not None and url.expires_at <= now:
        raise HTTPException(
            status_code=410,
            detail="This short URL has expired",
        )

    # Record the visit only after the URL is confirmed valid.
    click = Click(url_id=url.id)
    db.add(click)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return RedirectResponse(
        url=url.original_url,
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

