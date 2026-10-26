import app.api_key_models

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Identity,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    key_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
