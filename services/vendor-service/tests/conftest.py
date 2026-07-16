from __future__ import annotations

import os
import tempfile

# Must be set before `app.config`/`app.main` are imported anywhere.
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod-32bytes-min")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DOCUMENT_STORAGE_ROOT", tempfile.mkdtemp(prefix="sc-tpcrs-vendor-docs-"))
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

import pytest
from httpx import ASGITransport, AsyncClient
from sc_tpcrs_common.jwt_shared import create_access_token
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
async def _setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def auth_headers(role: str = "risk_officer", sub: str = "test-user@sc-tpcrs.demo") -> dict:
    token = create_access_token(subject=sub, role=role, mfa_verified=True, ttl_minutes=15)
    return {"Authorization": f"Bearer {token}"}
