"""The seed script self-mints a short-lived admin JWT using the shared
JWT_SECRET, the same "defense in depth" pattern risk-service uses to call
vendor-service internally (see services/risk-service/app/services/
internal_auth.py) -- no separate login/MFA flow needed just to seed data."""

from __future__ import annotations

from sc_tpcrs_common.jwt_shared import create_access_token

SEED_SUBJECT = "system:seed"


def admin_headers() -> dict[str, str]:
    token = create_access_token(subject=SEED_SUBJECT, role="admin", mfa_verified=True, ttl_minutes=30)
    return {"Authorization": f"Bearer {token}"}
