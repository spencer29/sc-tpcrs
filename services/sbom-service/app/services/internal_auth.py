"""Service-to-service authentication (same pattern as risk-service).

sbom-service calls vendor-service to resolve a vendor's name/tier for the
dependency graph. It self-mints a short-lived admin-role JWT with the shared
JWT_SECRET rather than routing through auth-service -- consistent with
jwt_shared.py's "any service may issue, every service independently verifies"
stance.
"""

from __future__ import annotations

import httpx
from sc_tpcrs_common.jwt_shared import create_access_token

from ..config import settings

SERVICE_SUBJECT = "system:sbom-service"


def service_auth_header() -> dict[str, str]:
    token = create_access_token(subject=SERVICE_SUBJECT, role="admin", mfa_verified=True, ttl_minutes=5)
    return {"Authorization": f"Bearer {token}"}


async def get_vendor_summary(vendor_id: str) -> dict | None:
    """Fetch {name, overall_tier} for a vendor, or None if unreachable/absent.

    Fails soft: the graph can still store the vendor by id if vendor-service is
    down; the name/tier are cosmetic enrichment.
    """
    url = f"{settings.vendor_service_url}/vendors/{vendor_id}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=service_auth_header())
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    return resp.json()
