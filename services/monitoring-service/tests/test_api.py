"""HTTP surface: RBAC, sweep trigger, alert lifecycle, dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.models import MonitoringAlert
from tests.conftest import TestSessionLocal, auth_headers


async def _make_alert(status: str = "open") -> MonitoringAlert:
    alert = MonitoringAlert(
        vendor_id=uuid.uuid4(),
        alert_type="POSTURE_DRIFT",
        severity="High",
        title="drift",
        description="d",
        dedup_key="POSTURE_DRIFT",
        status=status,
        source="sweep",
        details={},
        occurrence_count=1,
        first_seen_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        published=False,
    )
    async with TestSessionLocal() as db:
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
    return alert


# --- auth / RBAC ---
async def test_snapshots_requires_auth(client):
    resp = await client.get("/monitoring/snapshots")
    assert resp.status_code == 401


async def test_sweep_forbidden_for_non_writer(client):
    # compliance_manager is authenticated but not in the writer role set.
    resp = await client.post("/monitoring/sweep", headers=auth_headers(role="compliance_manager"))
    assert resp.status_code == 403


async def test_sweep_allowed_for_writer(client, stub_vendors):
    stub_vendors([str(uuid.uuid4()) for _ in range(2)])
    resp = await client.post("/monitoring/sweep", headers=auth_headers(role="risk_officer"))
    assert resp.status_code == 202
    body = resp.json()
    assert body["vendors_swept"] == 2
    assert body["snapshots_written"] == 2


async def test_snapshots_listed_after_sweep(client, stub_vendors):
    stub_vendors([str(uuid.uuid4())])
    await client.post("/monitoring/sweep", headers=auth_headers())
    resp = await client.get("/monitoring/snapshots", headers=auth_headers())
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# --- alert lifecycle ---
async def test_acknowledge_then_resolve(client):
    alert = await _make_alert()
    aid = str(alert.id)

    ack = await client.post(
        f"/monitoring/alerts/{aid}/acknowledge",
        json={"note": "looking into it"},
        headers=auth_headers(role="ciso"),
    )
    assert ack.status_code == 200
    assert ack.json()["status"] == "acknowledged"
    assert ack.json()["acknowledged_by"]

    res = await client.post(
        f"/monitoring/alerts/{aid}/resolve", json={"note": "fixed"}, headers=auth_headers(role="ciso")
    )
    assert res.status_code == 200
    assert res.json()["status"] == "resolved"


async def test_acknowledge_resolved_alert_conflicts(client):
    alert = await _make_alert(status="resolved")
    resp = await client.post(
        f"/monitoring/alerts/{alert.id}/acknowledge", json={}, headers=auth_headers()
    )
    assert resp.status_code == 409


async def test_acknowledge_forbidden_for_non_writer(client):
    alert = await _make_alert()
    resp = await client.post(
        f"/monitoring/alerts/{alert.id}/acknowledge",
        json={},
        headers=auth_headers(role="compliance_manager"),
    )
    assert resp.status_code == 403


async def test_get_missing_alert_404(client):
    resp = await client.get(f"/monitoring/alerts/{uuid.uuid4()}", headers=auth_headers())
    assert resp.status_code == 404


async def test_list_alerts_filter_by_status(client):
    await _make_alert(status="open")
    await _make_alert(status="resolved")
    resp = await client.get("/monitoring/alerts", params={"status": "open"}, headers=auth_headers())
    assert resp.status_code == 200
    assert all(a["status"] == "open" for a in resp.json())


# --- dashboard ---
async def test_dashboard_rolls_up_open_alerts(client):
    await _make_alert(status="open")
    resp = await client.get("/monitoring/dashboard", headers=auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["open_alerts"] >= 1
    assert "open_by_severity" in body
    assert "open_by_type" in body
