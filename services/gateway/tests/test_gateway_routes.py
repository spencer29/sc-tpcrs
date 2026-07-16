from __future__ import annotations

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient
from sc_tpcrs_common.jwt_shared import create_access_token
from starlette.responses import JSONResponse

from app import main as gateway_main


@pytest.fixture(autouse=True)
def _fake_redis():
    gateway_main.cache._client = fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
async def client():
    transport = ASGITransport(app=gateway_main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_unknown_route_returns_404(client):
    resp = await client.get("/api/nope/thing")
    assert resp.status_code == 404


async def test_protected_route_without_token_returns_401(client):
    resp = await client.get("/api/vendors")
    assert resp.status_code == 401


async def test_protected_route_forwards_with_identity_headers(client, monkeypatch):
    async def fake_forward(request, base_url, downstream_path, *, user_id, user_role):
        return JSONResponse({"base_url": base_url, "path": downstream_path, "user_id": user_id, "user_role": user_role})

    monkeypatch.setattr(gateway_main, "forward", fake_forward)
    token = create_access_token(subject="user@example.com", role="admin", mfa_verified=True, ttl_minutes=15)
    resp = await client.get("/api/vendors/123", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["path"] == "vendors/123"
    assert body["user_id"] == "user@example.com"
    assert body["user_role"] == "admin"


async def test_public_login_path_does_not_require_token(client, monkeypatch):
    async def fake_forward(request, base_url, downstream_path, *, user_id, user_role):
        return JSONResponse({"user_id": user_id})

    monkeypatch.setattr(gateway_main, "forward", fake_forward)
    resp = await client.post("/api/auth/login", json={"email": "a@b.com", "password": "x"})
    assert resp.status_code == 200
    assert resp.json()["user_id"] is None


async def test_rate_limit_exceeded_returns_429(client, monkeypatch):
    async def fake_forward(request, base_url, downstream_path, *, user_id, user_role):
        return JSONResponse({"ok": True})

    monkeypatch.setattr(gateway_main, "forward", fake_forward)
    monkeypatch.setattr(gateway_main.settings, "gateway_rate_limit_per_min", 2)

    token = create_access_token(subject="rl-user@example.com", role="admin", mfa_verified=True, ttl_minutes=15)
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(2):
        resp = await client.get("/api/vendors", headers=headers)
        assert resp.status_code == 200
    resp = await client.get("/api/vendors", headers=headers)
    assert resp.status_code == 429
