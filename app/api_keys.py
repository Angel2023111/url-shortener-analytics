
import hashlib
import secrets

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api_key_models import APIKey

from app.database import get_db
from app.database import get_db

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
)


def generate_api_key() -> str:
    """Generate a cryptographically secure API key."""
    return secrets.token_urlsafe(32)


def hash_api_key(raw_key: str) -> str:
    """Hash an API key before storing it."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def require_api_key(
    raw_key: str | None = Depends(api_key_header),
    db: Session = Depends(get_db),
) -> APIKey:
    """Reject requests without a valid, active API key."""
    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_hash = hash_api_key(raw_key)

    api_key = db.scalar(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active.is_(True),
        )
    )

    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
