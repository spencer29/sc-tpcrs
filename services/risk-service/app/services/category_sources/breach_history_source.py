"""Breach history VRS category (weight 15%). Sourced from the AbuseIPDB mock
adapter: 100 minus 15 points per abuse report in the last 24 months,
floored at 0."""

from __future__ import annotations

from sc_tpcrs_common.adapters import abuseipdb_adapter  # noqa: F401 - registers the adapter
from sc_tpcrs_common.adapters.registry import get_adapter


async def get_breach_history_score(vendor_id: str) -> float:
    adapter = get_adapter("abuseipdb")
    result = await adapter.fetch(vendor_id=vendor_id)
    report_count = int(result.data["report_count_24mo"])
    return max(0.0, round(100.0 - report_count * 15.0, 2))
