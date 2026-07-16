"""Single entrypoint: `docker compose --profile tools run --rm seed` (or
`make seed`). Orchestrates demo users, vendors (advanced through the real
onboarding workflow), tech-stack stubs, and an initial risk-score compute
pass, then writes seed/SEED_RESULTS.md (gitignored -- it documents this
specific run's generated UUIDs) so the manual verification walkthrough in
README.md has concrete values to check against.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

from .auth import admin_headers
from .config import RISK_SERVICE_URL
from .tech_stack import seed_tech_stack
from .users import seed_users
from .vendors import seed_vendors

RESULTS_PATH = Path(__file__).resolve().parent / "SEED_RESULTS.md"


def _compute_risk_scores(vendors: list[dict]) -> dict[str, dict]:
    results: dict[str, dict] = {}
    with httpx.Client(base_url=RISK_SERVICE_URL, timeout=30.0) as client:
        for vendor in vendors:
            if vendor["state"] not in ("QUESTIONNAIRE_COMPLETED", "ASSESSMENT_IN_PROGRESS", "ONBOARDED"):
                continue
            resp = client.post(f"/risk/vendors/{vendor['id']}/compute", headers=admin_headers())
            resp.raise_for_status()
            results[vendor["id"]] = resp.json()
    return results


def _write_results(users: dict, vendor_result: dict, risk_scores: dict[str, dict]) -> None:
    demo_id = vendor_result["demo_vendor_id"]
    demo_score = risk_scores.get(demo_id)

    lines = [
        "# Seed Results (generated -- not committed to git)",
        "",
        f"Demo users created this run: {len(users.get('created', []))} "
        f"(already existed: {len(users.get('already_existed', []))})",
        f"Demo user password: `{users.get('password')}`",
        "",
        f"Total vendors seeded: {len(vendor_result['vendors'])}",
        f"Risk scores computed: {len(risk_scores)}",
        "",
        "## Demo vendor (guaranteed critical CVE via left-pad@1.0.0)",
        f"- id: `{demo_id}`",
    ]
    if demo_score:
        lines += [
            f"- VRS: {demo_score['vrs_score']} (tier: {demo_score['tier']})",
            f"- questionnaire_score: {demo_score['questionnaire_score']} (expected 100.0 -- all-YES answers)",
            f"- vulnerability_score: {demo_score['vulnerability_score']} (expected 40.0 -- planted CVSS 9.8 KEV-listed CVE)",
            f"- compliance_score: {demo_score['compliance_score']} (expected 0.0 -- no documents uploaded)",
            f"- external_posture_score: {demo_score['external_posture_score']} (vendor-id-seeded mock, not hand-predictable ahead of time)",
            f"- breach_history_score: {demo_score['breach_history_score']}",
            f"- threat_intel_score: {demo_score['threat_intel_score']}",
        ]
    lines += [
        "",
        "## All seeded vendors",
        "",
        "| name | tier | state | vrs | risk_tier |",
        "|---|---|---|---|---|",
    ]
    for vendor in vendor_result["vendors"]:
        score = risk_scores.get(vendor["id"])
        vrs = score["vrs_score"] if score else "-"
        risk_tier = score["tier"] if score else "-"
        lines.append(f"| {vendor['name']} | {vendor['tier']} | {vendor['state']} | {vrs} | {risk_tier} |")

    text = "\n".join(lines) + "\n"
    RESULTS_PATH.write_text(text)
    print(text)


def main() -> None:
    print("Seeding demo users...")
    users = seed_users()
    print(f"  created={len(users['created'])} already_existed={len(users['already_existed'])}")

    print("Seeding vendors (real onboarding workflow, this takes a bit)...")
    vendor_result = seed_vendors()
    print(f"  {len(vendor_result['vendors'])} vendors created")

    print("Seeding vendor tech stacks...")
    seed_tech_stack(vendor_result["vendors"])

    print("Computing initial risk scores...")
    risk_scores = _compute_risk_scores(vendor_result["vendors"])
    print(f"  {len(risk_scores)} risk scores computed")

    _write_results(users, vendor_result, risk_scores)
    print(f"Results written to {RESULTS_PATH}")


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPStatusError as exc:
        print(f"Seeding failed: {exc.response.status_code} {exc.response.text}", file=sys.stderr)
        sys.exit(1)
