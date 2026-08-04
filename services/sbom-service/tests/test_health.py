from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "sbom-service"
    # Extended health surfaces the Neo4j mirror's reachability; disabled in
    # unit tests (NEO4J_ENABLED=false) so it degrades to False, not an error.
    assert body["neo4j"] is False
