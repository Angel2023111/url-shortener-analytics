from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class URLCreate(BaseModel):
    original_url: HttpUrl


class URLResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    short_code: str
    original_url: str
    short_url: str
    created_at: datetime
    expires_at: datetime | None
