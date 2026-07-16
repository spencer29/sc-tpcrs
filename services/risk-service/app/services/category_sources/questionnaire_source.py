"""Questionnaire self-assessment VRS category (weight 25%).

Reads the average score across answered questions directly from
vendor-service via REST. Fails soft to 0.0 (maximally unproven, not
skipped) on either a missing questionnaire or a vendor-service outage --
consistent with this project's "external dependency down should degrade,
not crash" posture (see redis_cache.py/kafka_base.py in shared/py-common).
"""

from __future__ import annotations

import logging

import httpx

from ...config import settings
from ..internal_auth import service_auth_header

logger = logging.getLogger("risk-service.questionnaire_source")


async def get_questionnaire_score(vendor_id: str) -> float:
    url = f"{settings.vendor_service_url}/vendors/{vendor_id}/questionnaire/score"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=service_auth_header())
    except httpx.HTTPError as exc:
        logger.warning("vendor-service unreachable while fetching questionnaire score: %s", exc)
        return 0.0

    if resp.status_code == 404:
        return 0.0
    resp.raise_for_status()
    return float(resp.json()["score"])
