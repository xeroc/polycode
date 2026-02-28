import os

from sqlalchemy import event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON, TypeDecorator

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./feature_dev.db")


class JSONType(TypeDecorator):
    """Platform-independent JSON type. Uses JSONB for PostgreSQL, JSON for others."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


__all__ = ["DATABASE_URL", "JSONType"]
