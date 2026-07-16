"""Cross-dialect UUID column type, shared by every service's SQLAlchemy models.

Uses PostgreSQL's native UUID type against a real Postgres database (asyncpg,
in every docker-compose/production run), and falls back to a 32-char
hex-encoded CHAR column under SQLite -- so each service's unit tests can run
against a fast in-memory SQLite DB without needing a live Postgres instance.
Standard SQLAlchemy "backend-agnostic GUID" recipe.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.engine import Dialect
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(str(value)).hex
        return value.hex

    def process_result_value(self, value: Any, dialect: Dialect) -> Any:
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(value)
        return value
