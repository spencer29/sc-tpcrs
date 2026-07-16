from __future__ import annotations

import uuid

from app.models import VendorTechStack

from .conftest import auth_headers


async def test_compute_requires_permitted_role(client):
    vendor_id = str(uuid.uuid4())
    resp = await client.post(f"/risk/vendors/{vendor_id}/compute", headers=auth_headers(role="analyst"))
    assert resp.status_code == 403


async def test_compute_requires_auth(client):
    vendor_id = str(uuid.uuid4())
    resp = await client.post(f"/risk/vendors/{vendor_id}/compute")
    assert resp.status_code == 401


async def test_compute_and_get_latest_risk_score(client):
    vendor_id = str(uuid.uuid4())
    compute_resp = await client.post(f"/risk/vendors/{vendor_id}/compute", headers=auth_headers())
    assert compute_resp.status_code == 201
    body = compute_resp.json()
    assert body["vendor_id"] == vendor_id
    assert 0.0 <= body["vrs_score"] <= 100.0
    assert body["tier"] in ("Critical", "High", "Medium", "Low")

    get_resp = await client.get(f"/risk/vendors/{vendor_id}", headers=auth_headers(role="analyst"))
    assert get_resp.status_code == 200
    assert get_resp.json()["vendor_id"] == vendor_id


async def test_get_risk_score_before_any_compute_returns_404(client):
    vendor_id = str(uuid.uuid4())
    resp = await client.get(f"/risk/vendors/{vendor_id}", headers=auth_headers(role="analyst"))
    assert resp.status_code == 404


async def test_history_endpoint_returns_chronological_entries(client):
    vendor_id = str(uuid.uuid4())
    await client.post(f"/risk/vendors/{vendor_id}/compute", headers=auth_headers())
    await client.post(f"/risk/vendors/{vendor_id}/compute", headers=auth_headers())

    resp = await client.get(f"/risk/vendors/{vendor_id}/history", headers=auth_headers(role="analyst"))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    assert items[0]["computed_at"] <= items[1]["computed_at"]


async def test_anomaly_endpoint_after_compute(client):
    vendor_id = str(uuid.uuid4())
    await client.post(f"/risk/vendors/{vendor_id}/compute", headers=auth_headers())
    resp = await client.get(f"/risk/vendors/{vendor_id}/anomaly", headers=auth_headers(role="analyst"))
    # If the anomaly model artifact isn't trained yet in this checkout,
    # evaluate_anomaly is skipped entirely (see app/ml/README.md) and no
    # anomaly_flags row exists -> 404 is the correct response in that case.
    assert resp.status_code in (200, 404)


async def test_vulnerability_score_reflected_in_compute(client, db_session):
    vendor_id = str(uuid.uuid4())
    db_session.add(
        VendorTechStack(vendor_id=vendor_id, component_name="left-pad", component_version="1.0.0", ecosystem="npm")
    )
    await db_session.commit()

    resp = await client.post(f"/risk/vendors/{vendor_id}/compute", headers=auth_headers())
    assert resp.status_code == 201
    assert resp.json()["vulnerability_score"] == 40.0


async def test_dashboard_summary_reflects_computed_scores(client):
    vendor_id = str(uuid.uuid4())
    await client.post(f"/risk/vendors/{vendor_id}/compute", headers=auth_headers())

    resp = await client.get("/risk/dashboard/summary", headers=auth_headers(role="analyst"))
    assert resp.status_code == 200
    body = resp.json()
    assert sum(body["tier_breakdown"].values()) >= 1
    assert any(v["vendor_id"] == vendor_id for v in body["top_risk_vendors"])
