"""Compliance status VRS category (weight 5%).

Reads the vendor's uploaded, typed evidence documents from vendor-service
and computes a weighted cert-presence score, capped at 100. Fails soft to
0.0 on a vendor-service outage.
"""

from __future__ import annotations

import logging

import httpx

from ...config import settings
from ..internal_auth import service_auth_header

logger = logging.getLogger("risk-service.compliance_source")

_DOCUMENT_TYPE_WEIGHTS: dict[str, float] = {
    "ISO27001_CERT": 40.0,
    "SOC2_REPORT": 30.0,
    "PCI_DSS_AOC": 20.0,
}
_DEFAULT_WEIGHT = 10.0


async def get_compliance_score(vendor_id: str) -> float:
    url = f"{settings.vendor_service_url}/vendors/{vendor_id}/documents"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=service_auth_header())
    except httpx.HTTPError as exc:
        logger.warning("vendor-service unreachable while fetching documents: %s", exc)
        return 0.0

    if resp.status_code == 404:
        return 0.0
    resp.raise_for_status()
    documents = resp.json()

    score = 0.0
    for doc in documents:
        score += _DOCUMENT_TYPE_WEIGHTS.get(doc["document_type"], _DEFAULT_WEIGHT)
    return min(100.0, round(score, 2))
