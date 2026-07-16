"""MISP threat-intelligence adapter.

Mock response gives a small, skewed-toward-zero count of IOC (indicator of
compromise) matches against a vendor's known assets, used to source
risk-service's "threat intelligence" VRS category.
"""

from __future__ import annotations

from typing import Any

from .base import AdapterResult, ExternalAdapter, seeded_random
from .registry import register_adapter


@register_adapter("misp")
class MispAdapter(ExternalAdapter):
    name = "misp"

    async def _fetch_mock(self, *, vendor_id: str, **_: Any) -> AdapterResult:
        rng = seeded_random("misp", vendor_id)
        roll = rng.random()
        if roll < 0.60:
            ioc_match_count = 0
        elif roll < 0.85:
            ioc_match_count = rng.randint(1, 2)
        else:
            ioc_match_count = rng.randint(3, 4)
        data = {
            "vendor_id": vendor_id,
            "ioc_match_count": ioc_match_count,
            "window_days": 30,
        }
        return AdapterResult.make(self.name, data, is_mock=True)
