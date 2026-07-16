"""Shodan external-security-posture adapter.

Mock response mirrors the shape risk-service needs for the "external security
posture" VRS category: a 0-100 posture score (higher = healthier/less
exposed) plus a small list of mock open ports/services, seeded deterministically
per vendor so repeated calls for the same vendor return the same result.
"""

from __future__ import annotations

from typing import Any

from .base import AdapterResult, ExternalAdapter, seeded_random
from .registry import register_adapter

_MOCK_SERVICES = ["ssh", "https", "http", "smtp", "rdp", "ftp", "dns"]


@register_adapter("shodan")
class ShodanAdapter(ExternalAdapter):
    name = "shodan"

    async def _fetch_mock(self, *, vendor_id: str, **_: Any) -> AdapterResult:
        rng = seeded_random("shodan", vendor_id)
        # Skew toward healthier postures (70-100) with a long tail down to 20.
        posture_score = round(min(100.0, max(0.0, rng.gauss(80, 15))), 1)
        open_port_count = rng.randint(0, 4)
        open_services = rng.sample(_MOCK_SERVICES, k=open_port_count) if open_port_count else []
        data = {
            "vendor_id": vendor_id,
            "posture_score": posture_score,
            "open_services": open_services,
            "last_scanned": "2024-06-01T00:00:00Z",
        }
        return AdapterResult.make(self.name, data, is_mock=True)
