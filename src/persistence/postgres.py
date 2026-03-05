"""PostgreSQL-based flow state persistence using SQLAlchemy with JSONB."""

import os
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from sqlalchemy import create_engine, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    Session,
    sessionmaker,
)
from sqlalchemy.types import String, DateTime, Integer
from sqlalchemy.types import JSON, TypeDecorator

from crewai.flow.persistence import FlowPersistence
from crewai.flow.async_feedback.types import PendingFeedbackContext


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@localhost:5432/chaoscraft"
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class JSONType(TypeDecorator):
    """Platform-independent JSON type. Uses JSONB for PostgreSQL, JSON for others."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class Requests(Base):
    """Flow state table model."""

    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_number: Mapped[int] = mapped_column(Integer, nullable=False)
    request_text: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


def update_request_status(
    session: sessionmaker, issue_number: int, status: str
) -> bool:
    """Update the status of a request by issue_number.

    Args:
        session: SQLAlchemy session factory
        issue_number: The issue_number to update
        status: The new status value

    Returns:
        True if a row was updated, False otherwise
    """
    with session() as sess:
        result = (
            sess.query(Requests)
            .filter_by(issue_number=issue_number)
            .update({"status": status})
        )
        sess.commit()
        return result > 0
