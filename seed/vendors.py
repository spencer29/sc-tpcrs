"""Creates and advances the seeded vendor population through the real
onboarding workflow (not a DB-level shortcut) so questionnaire scores and
lifecycle events are genuine, not faked."""

from __future__ import annotations

import random

import httpx

from .auth import admin_headers
from .config import SEED_RANDOM_SEED, VENDOR_SERVICE_URL
from .vendor_templates import DEMO_VENDOR, VENDOR_TEMPLATES

TIER_VALUES = ("Critical", "High", "Medium", "Low")
TIER_WEIGHTS = (0.15, 0.30, 0.35, 0.20)

# Target onboarding_state distribution across the 20 seeded vendors,
# including the 1 hardcoded demo vendor (counted within ONBOARDED).
STATE_PLAN: list[str] = (
    ["INITIATED"] * 3
    + ["QUESTIONNAIRE_SENT"] * 3
    + ["QUESTIONNAIRE_COMPLETED"] * 3
    + ["ASSESSMENT_IN_PROGRESS"] * 2
    + ["ONBOARDED"] * 6
    + ["REJECTED"] * 2
)

CERT_DOCUMENT_TYPES = ("ISO27001_CERT", "SOC2_REPORT", "PCI_DSS_AOC")


def _weighted_tier(rng: random.Random) -> str:
    return rng.choices(TIER_VALUES, weights=TIER_WEIGHTS, k=1)[0]


def _create_vendor(client: httpx.Client, name: str, legal_entity_name: str, industry: str, country: str, rng: random.Random) -> dict:
    payload = {
        "name": name,
        "legal_entity_name": legal_entity_name,
        "country": country,
        "industry": industry,
        "contact_name": "Compliance Contact",
        "contact_email": f"compliance@{name.lower().replace(' ', '-')}.example",
        "data_access_scope": _weighted_tier(rng),
        "service_criticality": _weighted_tier(rng),
        "integration_depth": _weighted_tier(rng),
    }
    resp = client.post("/vendors", json=payload, headers=admin_headers())
    resp.raise_for_status()
    return resp.json()


def _upload_sample_document(client: httpx.Client, vendor_id: str, document_type: str) -> None:
    files = {"file": (f"{document_type.lower()}.pdf", b"%PDF-1.4 seed-generated placeholder", "application/pdf")}
    resp = client.post(
        f"/vendors/{vendor_id}/documents", data={"document_type": document_type}, files=files, headers=admin_headers()
    )
    resp.raise_for_status()


def _advance_to_state(client: httpx.Client, vendor_id: str, target_state: str, rng: random.Random, *, all_yes: bool) -> None:
    if target_state == "INITIATED":
        return

    gen_resp = client.post(f"/vendors/{vendor_id}/questionnaire", headers=admin_headers())
    gen_resp.raise_for_status()
    questions = gen_resp.json()["questions"]

    if target_state == "QUESTIONNAIRE_SENT":
        return  # leave the questionnaire unanswered

    responses = []
    for q in questions:
        if all_yes:
            answer = "YES"
        else:
            roll = rng.random()
            answer = "YES" if roll < 0.6 else "PARTIAL" if roll < 0.85 else "NO" if roll < 0.95 else "NA"
        responses.append({"question_code": q["code"], "answer": answer})
    client.put(
        f"/vendors/{vendor_id}/questionnaire/responses", json={"responses": responses}, headers=admin_headers()
    ).raise_for_status()

    if target_state == "QUESTIONNAIRE_COMPLETED":
        return

    client.post(
        f"/vendors/{vendor_id}/transition", json={"target_state": "ASSESSMENT_IN_PROGRESS"}, headers=admin_headers()
    ).raise_for_status()
    if target_state == "ASSESSMENT_IN_PROGRESS":
        return

    client.post(
        f"/vendors/{vendor_id}/transition", json={"target_state": target_state}, headers=admin_headers()
    ).raise_for_status()


def seed_vendors() -> dict:
    """Returns {"vendors": [...], "demo_vendor_id": "..."}."""
    master_rng = random.Random(SEED_RANDOM_SEED)
    state_plan = list(STATE_PLAN)
    master_rng.shuffle(state_plan)
    # Guarantee the demo vendor gets ONBOARDED regardless of shuffle order.
    state_plan.remove("ONBOARDED")

    created: list[dict] = []
    with httpx.Client(base_url=VENDOR_SERVICE_URL, timeout=30.0) as client:
        # Demo vendor first: predictable inputs (Critical tier, all-YES
        # questionnaire, no compliance documents) so its category scores are
        # easy to hand-verify -- see seed/README.md.
        demo_rng = random.Random(f"{SEED_RANDOM_SEED}-demo")
        demo = _create_vendor(
            client, DEMO_VENDOR.name, DEMO_VENDOR.legal_entity_name, DEMO_VENDOR.industry, DEMO_VENDOR.country, demo_rng
        )
        # Force Critical tier deterministically regardless of the weighted roll.
        client.patch(
            f"/vendors/{demo['id']}",
            json={"data_access_scope": "Critical", "service_criticality": "Critical", "integration_depth": "Critical"},
            headers=admin_headers(),
        ).raise_for_status()
        _advance_to_state(client, demo["id"], "ONBOARDED", demo_rng, all_yes=True)
        created.append({"id": demo["id"], "name": demo["name"], "tier": "Critical", "state": "ONBOARDED", "is_demo": True})

        for index, template in enumerate(VENDOR_TEMPLATES):
            target_state = state_plan[index % len(state_plan)]
            vendor_rng = random.Random(f"{SEED_RANDOM_SEED}-{index}")
            vendor = _create_vendor(
                client, template.name, template.legal_entity_name, template.industry, template.country, vendor_rng
            )
            _advance_to_state(client, vendor["id"], target_state, vendor_rng, all_yes=False)

            if target_state == "ONBOARDED" and vendor_rng.random() < 0.7:
                _upload_sample_document(client, vendor["id"], vendor_rng.choice(CERT_DOCUMENT_TYPES))

            created.append(
                {"id": vendor["id"], "name": vendor["name"], "tier": vendor["overall_tier"], "state": target_state, "is_demo": False}
            )

    return {"vendors": created, "demo_vendor_id": demo["id"]}
