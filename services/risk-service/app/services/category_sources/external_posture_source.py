"""External security posture VRS category (weight 20%). Sourced directly
from the Shodan mock adapter's 0-100 posture score."""

from __future__ import annotations

from sc_tpcrs_common.adapters import shodan_adapter  # noqa: F401 - registers the adapter
from sc_tpcrs_common.adapters.registry import get_adapter


async def get_external_posture_score(vendor_id: str) -> float:
    adapter = get_adapter("shodan")
    result = await adapter.fetch(vendor_id=vendor_id)
    return float(result.data["posture_score"])
