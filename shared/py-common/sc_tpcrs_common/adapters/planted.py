"""Deterministic 'planted' findings that guarantee demo-scenario-critical
matches rather than relying purely on hashed randomness.

Demo Scenario 1 (critical CVE published -> SBOM cross-reference -> alerts)
requires ingesting an SBOM whose vulnerable component reliably resolves to a
CRITICAL, KEV-listed CVE. `seed/sboms.py` deliberately includes this exact
component/version in one seeded vendor's SBOM so the scenario is reliable
regardless of hash-seeded randomness elsewhere.
"""

PLANTED_VULNERABLE_COMPONENT = {"name": "left-pad", "version": "1.0.0", "ecosystem": "npm"}

PLANTED_CVE_ID = "CVE-2024-99999"

PLANTED_CVE_RECORD = {
    "cve_id": PLANTED_CVE_ID,
    "description": (
        "Planted demo vulnerability: prototype pollution leading to remote "
        "code execution in left-pad@1.0.0."
    ),
    "cvss_score": 9.8,
    "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "published": "2024-01-15T00:00:00Z",
}

PLANTED_KEV_RECORD = {
    "cve_id": PLANTED_CVE_ID,
    "vulnerability_name": "left-pad Prototype Pollution RCE (demo)",
    "date_added": "2024-01-20",
    "known_ransomware_use": False,
}


def is_planted(name: str, version: str) -> bool:
    return (
        name.lower() == PLANTED_VULNERABLE_COMPONENT["name"]
        and version == PLANTED_VULNERABLE_COMPONENT["version"]
    )
