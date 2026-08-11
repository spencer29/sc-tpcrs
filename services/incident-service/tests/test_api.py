from __future__ import annotations

import uuid

from tests.conftest import auth_headers

VENDOR = str(uuid.uuid4())


def _incident_payload(**over):
    body = {
        "vendor_id": VENDOR,
        "title": "Suspicious egress from vendor host",
        "description": "Beaconing to a known C2 endpoint.",
        "severity": "High",
        "category": "THREAT_INTEL",
    }
    body.update(over)
    return body


async def test_create_incident_requires_writer_role(client):
    # compliance_manager is read-only on incidents.
    resp = await client.post(
        "/incidents", json=_incident_payload(), headers=auth_headers(role="compliance_manager")
    )
    assert resp.status_code == 403


async def test_create_incident_as_risk_officer(client):
    resp = await client.post("/incidents", json=_incident_payload(), headers=auth_headers())
    assert resp.status_code == 201
    body = resp.json()
    assert body["reference"] == "INC-000001"
    assert body["status"] == "open"
    assert body["requires_cbn_notification"] is True
    # High severity + THREAT_INTEL -> a CBN draft was generated.
    assert any(n["regulator"] == "CBN" for n in body["notifications"])


async def test_create_requires_auth(client):
    resp = await client.post("/incidents", json=_incident_payload())
    assert resp.status_code in (401, 403)


async def test_list_and_filter_incidents(client):
    await client.post("/incidents", json=_incident_payload(severity="High"), headers=auth_headers())
    await client.post(
        "/incidents", json=_incident_payload(severity="Low", category="MANUAL"), headers=auth_headers()
    )
    resp = await client.get("/incidents?severity=Low", headers=auth_headers(role="compliance_manager"))
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["severity"] == "Low"


async def test_get_incident_detail_and_404(client):
    created = (await client.post("/incidents", json=_incident_payload(), headers=auth_headers())).json()
    ok = await client.get(f"/incidents/{created['id']}", headers=auth_headers())
    assert ok.status_code == 200
    assert ok.json()["id"] == created["id"]
    assert "timeline" in ok.json()

    missing = await client.get(f"/incidents/{uuid.uuid4()}", headers=auth_headers())
    assert missing.status_code == 404


async def test_status_transition_and_illegal_409(client):
    created = (await client.post("/incidents", json=_incident_payload(), headers=auth_headers())).json()
    iid = created["id"]

    ok = await client.post(
        f"/incidents/{iid}/status", json={"status": "investigating"}, headers=auth_headers()
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "investigating"

    # Jump straight to closed, then attempt to reopen to investigating -> illegal.
    await client.post(f"/incidents/{iid}/status", json={"status": "closed"}, headers=auth_headers())
    bad = await client.post(
        f"/incidents/{iid}/status", json={"status": "investigating"}, headers=auth_headers()
    )
    assert bad.status_code == 409


async def test_status_update_requires_writer(client):
    created = (await client.post("/incidents", json=_incident_payload(), headers=auth_headers())).json()
    resp = await client.post(
        f"/incidents/{created['id']}/status",
        json={"status": "investigating"},
        headers=auth_headers(role="compliance_manager"),
    )
    assert resp.status_code == 403


async def test_assign_and_note(client):
    created = (await client.post("/incidents", json=_incident_payload(), headers=auth_headers())).json()
    iid = created["id"]
    assigned = await client.post(
        f"/incidents/{iid}/assign", json={"assignee": "ciso@sc-tpcrs.demo"}, headers=auth_headers(role="ciso")
    )
    assert assigned.status_code == 200
    assert assigned.json()["assignee"] == "ciso@sc-tpcrs.demo"

    noted = await client.post(
        f"/incidents/{iid}/notes", json={"message": "Contained at firewall."}, headers=auth_headers()
    )
    assert noted.status_code == 200
    assert any(t["event_type"] == "note" for t in noted.json()["timeline"])


async def test_timeline_and_notifications_endpoints(client):
    created = (
        await client.post(
            "/incidents",
            json=_incident_payload(severity="Critical", category="DATA_BREACH", personal_data_involved=True),
            headers=auth_headers(),
        )
    ).json()
    iid = created["id"]
    tl = await client.get(f"/incidents/{iid}/timeline", headers=auth_headers())
    assert tl.status_code == 200 and len(tl.json()) >= 1

    notes = await client.get(f"/incidents/{iid}/notifications", headers=auth_headers())
    assert notes.status_code == 200
    regulators = {n["regulator"] for n in notes.json()}
    assert regulators == {"CBN", "NDPC"}


async def test_dashboard_rollup(client):
    await client.post("/incidents", json=_incident_payload(severity="High"), headers=auth_headers())
    critical = (
        await client.post(
            "/incidents", json=_incident_payload(severity="Critical"), headers=auth_headers()
        )
    ).json()
    # Drive one to contained so mean-time-to-contain is populated.
    await client.post(
        f"/incidents/{critical['id']}/status", json={"status": "contained"}, headers=auth_headers()
    )

    dash = await client.get("/incidents/dashboard", headers=auth_headers(role="compliance_manager"))
    assert dash.status_code == 200
    body = dash.json()
    assert body["total_incidents"] == 2
    assert body["open_by_severity"]["High"] == 1
    assert body["open_by_severity"]["Critical"] == 1
    assert body["pending_notifications"] >= 2
    assert body["mean_time_to_contain_hours"] is not None
