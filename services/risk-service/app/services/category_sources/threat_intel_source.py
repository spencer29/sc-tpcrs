"""Threat intelligence VRS category (weight 15%). Sourced from the MISP mock
adapter: 100 minus 10 points per IOC match in the last 30 days, floored
at 0."""

from __future__ import annotations

from sc_tpcrs_common.adapters import misp_adapter  # noqa: F401 - registers the adapter
from sc_tpcrs_common.adapters.registry import get_adapter


async def get_threat_intel_score(vendor_id: str) -> float:
    adapter = get_adapter("misp")
    result = await adapter.fetch(vendor_id=vendor_id)
    match_count = int(result.data["ioc_match_count"])
    return max(0.0, round(100.0 - match_count * 10.0, 2))
