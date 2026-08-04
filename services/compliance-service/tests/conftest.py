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
def _stub_kafka(monkeypatch):
    """The lifespan builds a consumer and endpoints publish events; neither
    should touch a real broker in tests (producer.start() blocks on a connect
    *timeout* when no broker is present -- not a KafkaConnectionError -- so
    fail-soft alone doesn't save us). Stub the producer + consumer to no-ops."""
    from app.routers import compliance as compliance_router
    from app.services import events

    async def _noop_publish(*_a, **_k):
        return False

    async def _noop(*_a, **_k):
        return None

    monkeypatch.setattr(events._producer, "publish", _noop_publish)
    monkeypatch.setattr(events._producer, "close", _noop)
    # The compliance router imported publish_assessment_event into its own
    # namespace -- patch that binding (and the source) to a no-op.
    monkeypatch.setattr(events, "publish_assessment_event", _noop_publish)
    monkeypatch.setattr(compliance_router, "publish_assessment_event", _noop_publish)
    # ASGITransport doesn't run the lifespan, but stub the consumer's
    # background loop defensively in case a test drives it.
    monkeypatch.setattr(app_main._consumer, "start_background", lambda: None)

    async def _noop_stop():
        return None

    monkeypatch.setattr(app_main._consumer, "stop", _noop_stop)


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


def auth_headers(role: str = "compliance_manager", sub: str = "compliance1@sc-tpcrs.demo") -> dict:
    token = create_access_token(subject=sub, role=role, mfa_verified=True, ttl_minutes=15)
    return {"Authorization": f"Bearer {token}"}
