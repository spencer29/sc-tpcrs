"""NVD (National Vulnerability Database) adapter.

Mock response shape mirrors NVD API v2.0's essential fields
(cve id / description / CVSS v3.1 base score / published date) so that
`sbom-service`'s parsing code needs no changes if NVD_MODE=real is enabled
later with a real NVD_API_KEY.
"""

from __future__ import annotations

from typing import Any

from .base import AdapterResult, ExternalAdapter, seeded_random
from .planted import PLANTED_CVE_RECORD, is_planted
from .registry import register_adapter


@register_adapter("nvd")
class NvdAdapter(ExternalAdapter):
    name = "nvd"

    async def _fetch_mock(
        self, *, component_name: str, version: str, ecosystem: str = "generic", **_: Any
    ) -> AdapterResult:
        if is_planted(component_name, version):
            return AdapterResult.make(self.name, [dict(PLANTED_CVE_RECORD)], is_mock=True)

        rng = seeded_random("nvd", component_name, version)
        if rng.random() < 0.30:
            # ~30% of components have no known CVEs in the mock world.
            return AdapterResult.make(self.name, [], is_mock=True)

        cve_count = rng.randint(1, 3)
        cves = []
        for i in range(cve_count):
            severity_roll = rng.random()
            if severity_roll < 0.10:
                score = round(rng.uniform(9.0, 10.0), 1)
            elif severity_roll < 0.35:
                score = round(rng.uniform(7.0, 8.9), 1)
            elif severity_roll < 0.70:
                score = round(rng.uniform(4.0, 6.9), 1)
            else:
                score = round(rng.uniform(0.1, 3.9), 1)
            cve_id = f"CVE-{2020 + rng.randint(0, 5)}-{rng.randint(1000, 99999)}"
            cves.append(
                {
                    "cve_id": cve_id,
                    "description": f"Mock vulnerability #{i + 1} affecting {component_name}@{version} ({ecosystem}).",
                    "cvss_score": score,
                    "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:L/A:N",
                    "published": "2023-06-01T00:00:00Z",
                }
            )
        return AdapterResult.make(self.name, cves, is_mock=True)
