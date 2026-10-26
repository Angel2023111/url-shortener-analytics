
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from collections.abc import Generator
from sqlalchemy.orm import Session

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://url_app:change_this_local_password@localhost:5432/url_shortener",
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
