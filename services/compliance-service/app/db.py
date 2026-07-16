from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    """No models yet -- schema lands in a future build pass. This
    engine/session scaffold exists so the Dockerfile/compose topology and
    future migrations have a stable place to attach to without re-plumbing
    the service."""
