"""CISA Known Exploited Vulnerabilities (KEV) catalogue adapter.

Mock response shape mirrors CISA's KEV catalogue essential fields
(cve_id / vulnerability_name / date_added / known_ransomware_use) so a future
KEV_MODE=real switch requires no downstream parsing changes.
"""

from __future__ import annotations

from typing import Any

from .base import AdapterResult, ExternalAdapter, seeded_random
from .planted import PLANTED_KEV_RECORD, is_planted
from .registry import register_adapter


@register_adapter("kev")
class KevAdapter(ExternalAdapter):
    name = "kev"

    async def _fetch_mock(
        self, *, cve_id: str, component_name: str = "", version: str = "", **_: Any
    ) -> AdapterResult:
        if component_name and version and is_planted(component_name, version):
            return AdapterResult.make(self.name, dict(PLANTED_KEV_RECORD), is_mock=True)

        rng = seeded_random("kev", cve_id)
        if rng.random() < 0.15:
            # ~15% of mock CVEs are KEV-listed.
            record = {
                "cve_id": cve_id,
                "vulnerability_name": f"Mock actively-exploited issue in {cve_id}",
                "date_added": "2024-03-01",
                "known_ransomware_use": rng.random() < 0.2,
            }
            return AdapterResult.make(self.name, record, is_mock=True)
        return AdapterResult.make(self.name, None, is_mock=True)
