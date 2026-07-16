"""Seeds risk-service's vendor_tech_stack stub (stand-in for real SBOM
ingestion -- see services/risk-service/app/models.py) via its internal
admin-only HTTP endpoint. The demo vendor always gets left-pad@1.0.0/npm,
matching shared/py-common/sc_tpcrs_common/adapters/planted.py's guaranteed
critical/KEV-listed CVE fixture."""

from __future__ import annotations

import random

import httpx

from .auth import admin_headers
from .config import RISK_SERVICE_URL

_MOCK_COMPONENT_POOL: tuple[tuple[str, str, str], ...] = (
    ("express", "4.18.2", "npm"),
    ("lodash", "4.17.21", "npm"),
    ("requests", "2.31.0", "pypi"),
    ("django", "4.2.1", "pypi"),
    ("spring-core", "5.3.27", "maven"),
    ("openssl", "3.0.9", "generic"),
    ("axios", "1.4.0", "npm"),
    ("flask", "2.3.2", "pypi"),
    ("jackson-databind", "2.15.2", "maven"),
    ("react", "18.2.0", "npm"),
)


def seed_tech_stack(vendors: list[dict]) -> None:
    with httpx.Client(base_url=RISK_SERVICE_URL, timeout=30.0) as client:
        for vendor in vendors:
            if vendor["is_demo"]:
                components = [{"component_name": "left-pad", "component_version": "1.0.0", "ecosystem": "npm"}]
            else:
                rng = random.Random(f"tech-stack-{vendor['id']}")
                sample = rng.sample(_MOCK_COMPONENT_POOL, k=rng.randint(2, 5))
                components = [
                    {"component_name": name, "component_version": version, "ecosystem": ecosystem}
                    for name, version, ecosystem in sample
                ]
            resp = client.post(
                f"/internal/vendors/{vendor['id']}/tech-stack",
                json={"components": components},
                headers=admin_headers(),
            )
            resp.raise_for_status()
