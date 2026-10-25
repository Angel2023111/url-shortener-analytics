
import os
import secrets
import string
from collections.abc import Generator

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import URL
from app.schemas import URLCreate, URLResponse

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
