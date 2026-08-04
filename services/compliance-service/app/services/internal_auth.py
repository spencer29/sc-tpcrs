"""Service-to-service authentication (self-minted short-lived admin JWT).

See risk-service's internal_auth for the rationale: every service holds the
shared JWT_SECRET, so compliance-service mints its own token to call
vendor-service rather than routing through auth-service.
"""

from __future__ import annotations

from sc_tpcrs_common.jwt_shared import create_access_token

SERVICE_SUBJECT = "system:compliance-service"


def service_auth_header() -> dict[str, str]:
    token = create_access_token(subject=SERVICE_SUBJECT, role="admin", mfa_verified=True, ttl_minutes=5)
    return {"Authorization": f"Bearer {token}"}
