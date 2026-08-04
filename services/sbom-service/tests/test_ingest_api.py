from __future__ import annotations

import json
import uuid

from .conftest import auth_headers

# Demo Scenario 1: a CycloneDX SBOM containing the planted left-pad@1.0.0
# component, which must resolve to the CRITICAL, KEV-listed CVE-2024-99999.
DEMO_VENDOR_ID = str(uuid.uuid4())

DEMO_SBOM = json.dumps(
    {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "metadata": {"component": {"name": "paystack-checkout", "type": "application"}},
        "components": [
            {
                "type": "library",
                "name": "left-pad",
                "version": "1.0.0",
                "purl": "pkg:npm/left-pad@1.0.0",
            },
            {"type": "library", "name": "express", "version": "4.18.2", "purl": "pkg:npm/express@4.18.2"},
            # A component with no purl -> must be synthesised + flag the doc incomplete.
            {"type": "library", "name": "internal-utils", "version": "0.9.0"},
        ],
    }
)


async def test_ingest_requires_authentication(client):
    resp = await client.post(
        "/sbom/ingest",
        json={"vendor_id": DEMO_VENDOR_ID, "content": DEMO_SBOM},
    )
    assert resp.status_code == 401


async def test_ingest_forbidden_for_wrong_role(client):
    resp = await client.post(
        "/sbom/ingest",
        json={"vendor_id": DEMO_VENDOR_ID, "content": DEMO_SBOM},
        # compliance_manager is a valid role but NOT in the ingest allow-list
        # (risk_officer / ciso / admin) -> must be forbidden.
        headers=auth_headers(role="compliance_manager"),
    )
    assert resp.status_code == 403


async def test_ingest_rejects_garbage_with_422(client):
    resp = await client.post(
        "/sbom/ingest",
        json={"vendor_id": DEMO_VENDOR_ID, "content": "this is not an SBOM"},
        headers=auth_headers(),
    )
    assert resp.status_code == 422


async def test_demo_scenario_1_left_pad_resolves_to_critical_kev_cve(client):
    resp = await client.post(
        "/sbom/ingest",
        json={
            "vendor_id": DEMO_VENDOR_ID,
            "content": DEMO_SBOM,
            "document_name": "paystack-checkout.cdx.json",
        },
        headers=auth_headers(role="risk_officer"),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()

    # Document-level assertions.
    doc = body["document"]
    assert doc["sbom_format"] == "CycloneDX"
    assert doc["component_count"] == 3
    assert doc["vulnerable_count"] >= 1
    # internal-utils had no purl -> synthesised -> doc flagged for manual review.
    assert doc["incomplete"] is True

    # The planted CVE must surface in the critical roll-up.
    crit = body["critical_vulnerabilities"]
    cve_ids = {v["cve_id"] for v in crit}
    assert "CVE-2024-99999" in cve_ids
    planted = next(v for v in crit if v["cve_id"] == "CVE-2024-99999")
    assert planted["severity"] == "Critical"
    assert planted["kev_flag"] is True
    assert planted["ssvc_priority"] == "Act"

    # The component tree must carry the synthesised-purl flag.
    by_name = {c["component_name"]: c for c in body["components"]}
    assert by_name["internal-utils"]["purl_synthesised"] is True
    assert by_name["left-pad"]["purl_synthesised"] is False

    # SLA sanity: 3 components well under the 5s / 1000-component budget.
    assert body["processing_ms"] < 5000


async def test_cve_impact_returns_affected_component_across_portfolio(client):
    # Ingest first so there is something to cross-reference.
    ingest = await client.post(
        "/sbom/ingest",
        json={"vendor_id": DEMO_VENDOR_ID, "content": DEMO_SBOM},
        headers=auth_headers(),
    )
    assert ingest.status_code == 201, ingest.text

    resp = await client.get(
        "/sbom/graph/cve/CVE-2024-99999/impact",
        headers=auth_headers(),
    )
    assert resp.status_code == 200, resp.text
    affected = resp.json()
    names = {c["component_name"] for c in affected}
    assert "left-pad" in names
    lp = next(c for c in affected if c["component_name"] == "left-pad")
    assert any(v["cve_id"] == "CVE-2024-99999" for v in lp["vulnerabilities"])


async def test_vendor_document_and_component_listings(client):
    await client.post(
        "/sbom/ingest",
        json={"vendor_id": DEMO_VENDOR_ID, "content": DEMO_SBOM},
        headers=auth_headers(),
    )

    docs = await client.get(
        f"/sbom/vendors/{DEMO_VENDOR_ID}/documents", headers=auth_headers()
    )
    assert docs.status_code == 200
    assert len(docs.json()) >= 1

    vuln_only = await client.get(
        f"/sbom/vendors/{DEMO_VENDOR_ID}/components?vulnerable_only=true",
        headers=auth_headers(),
    )
    assert vuln_only.status_code == 200
    returned = vuln_only.json()
    names = {c["component_name"] for c in returned}
    # left-pad is the planted component -> deterministically vulnerable.
    assert "left-pad" in names
    # vulnerable_only must never return a component with an empty vuln list.
    assert all(c["vulnerabilities"] for c in returned)
