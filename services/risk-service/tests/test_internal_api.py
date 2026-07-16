from __future__ import annotations

import uuid

from .conftest import auth_headers


async def test_add_tech_stack_requires_admin(client):
    vendor_id = str(uuid.uuid4())
    resp = await client.post(
        f"/internal/vendors/{vendor_id}/tech-stack",
        json={"components": [{"component_name": "left-pad", "component_version": "1.0.0", "ecosystem": "npm"}]},
        headers=auth_headers(role="risk_officer"),
    )
    assert resp.status_code == 403


async def test_add_tech_stack_and_reflected_in_vulnerability_score(client):
    vendor_id = str(uuid.uuid4())
    add_resp = await client.post(
        f"/internal/vendors/{vendor_id}/tech-stack",
        json={"components": [{"component_name": "left-pad", "component_version": "1.0.0", "ecosystem": "npm"}]},
        headers=auth_headers(role="admin"),
    )
    assert add_resp.status_code == 201
    assert add_resp.json()["components_added"] == 1

    compute_resp = await client.post(f"/risk/vendors/{vendor_id}/compute", headers=auth_headers())
    assert compute_resp.status_code == 201
    assert compute_resp.json()["vulnerability_score"] == 40.0
