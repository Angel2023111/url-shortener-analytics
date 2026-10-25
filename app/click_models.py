
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Click(Base):
    __tablename__ = "clicks"

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    url_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("urls.id", ondelete="CASCADE"),
        nullable=False,
    )

    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
