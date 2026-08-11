"""Service-to-service authentication (see risk-service's internal_auth for the
rationale). monitoring-service calls vendor-service to enumerate the vendor
portfolio to sweep; it self-mints a short-lived admin JWT with the shared
JWT_SECRET rather than routing through auth-service."""

from __future__ import annotations

from sc_tpcrs_common.jwt_shared import create_access_token

SERVICE_SUBJECT = "system:monitoring-service"


def service_auth_header() -> dict[str, str]:
    token = create_access_token(subject=SERVICE_SUBJECT, role="admin", mfa_verified=True, ttl_minutes=5)
    return {"Authorization": f"Bearer {token}"}
