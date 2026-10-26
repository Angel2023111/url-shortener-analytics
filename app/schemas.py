from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator


class URLCreate(BaseModel):
    original_url: HttpUrl
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def validate_expires_at(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("expires_at must include a timezone")

        if value <= datetime.now(timezone.utc):
            raise ValueError("expires_at must be in the future")

        return value


class URLResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    short_code: str
    original_url: str
    short_url: str
    created_at: datetime
    expires_at: datetime | None

