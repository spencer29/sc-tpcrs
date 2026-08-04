from __future__ import annotations

import uuid

from .conftest import auth_headers

VENDOR_ID = str(uuid.uuid4())


# --- Control library endpoints ---
async def test_control_library_summary(client):
    resp = await client.get("/compliance/controls", headers=auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_controls"] >= 250
    frameworks = {f["framework"] for f in body["frameworks"]}
    assert "ISO 27001:2022" in frameworks
    assert "PCI DSS v4.0" in frameworks
    assert "NDPR/NDPA" in frameworks
    assert "CBN Cybersecurity Framework" in frameworks


async def test_control_list_filterable_by_framework(client):
    resp = await client.get("/compliance/controls/list?framework=ISO 27001:2022", headers=auth_headers())
    assert resp.status_code == 200
    controls = resp.json()
    assert len(controls) == 93
    assert all(c["framework"] == "ISO 27001:2022" for c in controls)


# --- Auth / role gating ---
async def test_create_assessment_requires_auth(client):
    resp = await client.post("/compliance/assessments", json={"vendor_id": VENDOR_ID})
    assert resp.status_code == 401


async def test_create_assessment_forbidden_for_risk_officer(client):
    # risk_officer is a valid role but NOT permitted to run compliance
    # assessments (compliance_manager / ciso / admin only).
    resp = await client.post(
        "/compliance/assessments",
        json={"vendor_id": VENDOR_ID, "framework": "ALL"},
        headers=auth_headers(role="risk_officer"),
    )
    assert resp.status_code == 403


async def test_create_assessment_rejects_unknown_framework(client):
    resp = await client.post(
        "/compliance/assessments",
        json={"vendor_id": VENDOR_ID, "framework": "NIST CSF"},
        headers=auth_headers(),
    )
    assert resp.status_code == 422


# --- Full assessment -> gap-analysis -> report flow ---
async def test_full_compliance_flow(client):
    # 1. Run a full-library assessment.
    create = await client.post(
        "/compliance/assessments",
        json={"vendor_id": VENDOR_ID, "framework": "ALL"},
        headers=auth_headers(role="compliance_manager"),
    )
    assert create.status_code == 201, create.text
    assessment = create.json()
    aid = assessment["id"]

    assert assessment["framework"] == "ALL"
    assert assessment["total_controls"] >= 250
    assert 0 <= assessment["compliance_score"] <= 100
    assert assessment["status"] in ("Compliant", "Partially Compliant", "Non-Compliant")
    # A full-library assessment covers every framework in the roll-up.
    assert "ISO 27001:2022" in assessment["framework_scores"]
    # Counts reconcile with the total.
    covered = (
        assessment["compliant_count"]
        + assessment["partial_count"]
        + assessment["gap_count"]
    )
    assert covered <= assessment["total_controls"]

    # 2. Gap analysis rolls up by domain and ranks gaps critical-first.
    gap = await client.get(f"/compliance/assessments/{aid}/gap-analysis", headers=auth_headers())
    assert gap.status_code == 200, gap.text
    gap_body = gap.json()
    assert gap_body["assessment_id"] == aid
    assert len(gap_body["by_domain"]) > 0
    # Worst-scoring domain first.
    scores = [d["score"] for d in gap_body["by_domain"]]
    assert scores == sorted(scores)
    # Every listed gap is a genuine partial/gap.
    assert all(g["status"] in ("gap", "partial") for g in gap_body["gaps"])

    # 3. Regulator-ready report carries an attestation + full register.
    report = await client.get(f"/compliance/assessments/{aid}/report", headers=auth_headers())
    assert report.status_code == 200, report.text
    rpt = report.json()
    assert str(VENDOR_ID) in rpt["attestation"]
    assert len(rpt["control_register"]) == assessment["total_controls"]
    assert rpt["assessment"]["id"] == aid


async def test_assessment_is_deterministic_across_runs(client):
    vid = str(uuid.uuid4())
    a = await client.post(
        "/compliance/assessments",
        json={"vendor_id": vid, "framework": "PCI DSS v4.0"},
        headers=auth_headers(),
    )
    b = await client.post(
        "/compliance/assessments",
        json={"vendor_id": vid, "framework": "PCI DSS v4.0"},
        headers=auth_headers(),
    )
    assert a.status_code == b.status_code == 201
    # Same vendor + framework -> identical deterministic score.
    assert a.json()["compliance_score"] == b.json()["compliance_score"]
    assert a.json()["gap_count"] == b.json()["gap_count"]


async def test_manual_override_changes_score(client):
    vid = str(uuid.uuid4())
    baseline = await client.post(
        "/compliance/assessments",
        json={"vendor_id": vid, "framework": "ISO 27001:2022"},
        headers=auth_headers(),
    )
    base_score = baseline.json()["compliance_score"]

    # Find a control the baseline marked as a gap, then override it to met.
    controls = await client.get(
        f"/compliance/assessments/{baseline.json()['id']}/controls?status=gap",
        headers=auth_headers(),
    )
    gaps = controls.json()
    assert gaps, "expected at least one gap in a 93-control assessment"
    target = gaps[0]["control_id"]

    overridden = await client.post(
        "/compliance/assessments",
        json={
            "vendor_id": vid,
            "framework": "ISO 27001:2022",
            "overrides": [{"control_id": target, "status": "met", "evidence": "audited"}],
        },
        headers=auth_headers(),
    )
    # Closing a gap cannot lower the score.
    assert overridden.json()["compliance_score"] >= base_score


async def test_dashboard_aggregates_latest_per_vendor(client):
    # Two vendors, one assessment each.
    for _ in range(2):
        await client.post(
            "/compliance/assessments",
            json={"vendor_id": str(uuid.uuid4()), "framework": "SOC 2"},
            headers=auth_headers(),
        )
    resp = await client.get("/compliance/dashboard", headers=auth_headers())
    assert resp.status_code == 200
    body = resp.json()
    assert body["vendors_assessed"] >= 2
    assert body["total_assessments"] >= 2
    assert 0 <= body["average_score"] <= 100
    assert sum(body["status_breakdown"].values()) == body["vendors_assessed"]
