"""Custom SQLAlchemy types that work across dialects (PG, SQLite for tests)."""

from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator


class JSONColumn(TypeDecorator):
    """JSONB on Postgres, JSON elsewhere (notably SQLite for tests)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())
