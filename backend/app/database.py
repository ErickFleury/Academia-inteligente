"""Database configuration and declarative base shared by domain modules."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for application-owned persistence models."""


database_url = os.environ.get("DATABASE_URL", "")
engine = create_engine(database_url, pool_pre_ping=True) if database_url else None
SessionLocal = (
    sessionmaker(bind=engine, autoflush=False, expire_on_commit=False) if engine else None
)


def get_database_session() -> Generator[Session, None, None]:
    """Provide one transaction-capable session per request."""
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL must be configured")

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
