"""Service-to-service authentication.

risk-service calls vendor-service's internal endpoints (questionnaire score,
document list) over plain REST. Rather than adding a network hop through
auth-service, it self-mints a short-lived admin-role JWT using the same
shared JWT_SECRET every service already holds -- consistent with
jwt_shared.py's documented "defense in depth" stance (every service
independently validates tokens; who *issues* a token is not restricted to
auth-service).
"""

from __future__ import annotations

from sc_tpcrs_common.jwt_shared import create_access_token

SERVICE_SUBJECT = "system:risk-service"


def service_auth_header() -> dict[str, str]:
    token = create_access_token(subject=SERVICE_SUBJECT, role="admin", mfa_verified=True, ttl_minutes=5)
    return {"Authorization": f"Bearer {token}"}
