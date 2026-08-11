from __future__ import annotations

import os

# Must be set before `app.config`/`app.main` are imported anywhere.
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod-32bytes-min")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
os.environ.setdefault("VENDOR_SERVICE_URL", "http://127.0.0.1:1")

import pytest
from httpx import ASGITransport, AsyncClient
from sc_tpcrs_common.jwt_shared import create_access_token
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app import main as app_main
from app.db import Base, get_db

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


app_main.app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _stub_kafka_and_scheduler(monkeypatch):
    """Keep tests off a real broker and out of the background sweep loop.

    The producer's start()/publish() block on a connect *timeout* when no
    broker is present (not a KafkaConnectionError, so fail-soft alone doesn't
    save us). We stub the producer publish + the consumer/scheduler lifecycle
    to no-ops. ASGITransport doesn't run the lifespan, but stub defensively."""
    from app.services import events

    async def _noop_publish(*_a, **_k):
        return True

    async def _noop(*_a, **_k):
        return None

    monkeypatch.setattr(events._producer, "publish", _noop_publish)
    monkeypatch.setattr(events._producer, "close", _noop, raising=False)
    monkeypatch.setattr(app_main._consumer, "start_background", lambda: None)
    monkeypatch.setattr(app_main._consumer, "stop", _noop)
    monkeypatch.setattr(app_main._scheduler, "start_background", lambda: None)
    monkeypatch.setattr(app_main._scheduler, "stop", _noop)


@pytest.fixture
def stub_vendors(monkeypatch):
    """Override vendor_client.list_vendor_ids with a fixed portfolio.

    Returns a callable that installs the given list of vendor ids so a test can
    control exactly which vendors a sweep touches."""

    def _install(vendor_ids: list[str]):
        async def _fake_list(limit: int = 200):
            return [{"id": vid, "name": f"Vendor {i}"} for i, vid in enumerate(vendor_ids)][:limit]

        # Patch the binding used inside sweep_service (imported as a module).
        from app.services import sweep_service, vendor_client

        monkeypatch.setattr(vendor_client, "list_vendor_ids", _fake_list)
        monkeypatch.setattr(sweep_service.vendor_client, "list_vendor_ids", _fake_list)

    return _install


@pytest.fixture(autouse=True)
async def _setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client():
    transport = ASGITransport(app=app_main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def auth_headers(role: str = "risk_officer", sub: str = "risk1@sc-tpcrs.demo") -> dict:
    token = create_access_token(subject=sub, role=role, mfa_verified=True, ttl_minutes=15)
    return {"Authorization": f"Bearer {token}"}
