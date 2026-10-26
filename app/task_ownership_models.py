from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

import app.task_ownership_models


class TaskOwnership(Base):
    __tablename__ = "task_ownership"

    task_id: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
    )

    api_key_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("api_keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )