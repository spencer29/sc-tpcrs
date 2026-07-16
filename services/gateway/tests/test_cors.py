from __future__ import annotations

import fakeredis.aioredis
import pytest
from httpx import ASGITransport, AsyncClient

from app import main as gateway_main


@pytest.fixture(autouse=True)
def _fake_redis():
    gateway_main.cache._client = fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
async def client():
    transport = ASGITransport(app=gateway_main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_cors_preflight_allows_configured_frontend_origin(client):
    resp = await client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_cors_actual_request_echoes_allowed_origin(client, monkeypatch):
    from starlette.responses import JSONResponse

    async def fake_forward(request, base_url, downstream_path, *, user_id, user_role):
        return JSONResponse({"ok": True})

    monkeypatch.setattr(gateway_main, "forward", fake_forward)
    resp = await client.post(
        "/api/auth/login",
        json={"email": "a@b.com", "password": "x"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"
