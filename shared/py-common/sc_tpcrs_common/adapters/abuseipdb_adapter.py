"""AbuseIPDB breach/abuse-history adapter.

Mock response gives a small, skewed-toward-zero count of abuse reports for a
vendor's assets over the last 24 months, used to source risk-service's
"breach history" VRS category.
"""

from __future__ import annotations

from typing import Any

from .base import AdapterResult, ExternalAdapter, seeded_random
from .registry import register_adapter


@register_adapter("abuseipdb")
class AbuseIpDbAdapter(ExternalAdapter):
    name = "abuseipdb"

    async def _fetch_mock(self, *, vendor_id: str, **_: Any) -> AdapterResult:
        rng = seeded_random("abuseipdb", vendor_id)
        # Weighted toward 0 reports: ~55% chance of 0, tail up to 5.
        roll = rng.random()
        if roll < 0.55:
            report_count = 0
        elif roll < 0.80:
            report_count = rng.randint(1, 2)
        else:
            report_count = rng.randint(3, 5)
        data = {
            "vendor_id": vendor_id,
            "report_count_24mo": report_count,
            "period_months": 24,
        }
        return AdapterResult.make(self.name, data, is_mock=True)
