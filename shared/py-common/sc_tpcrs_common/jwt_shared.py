"""Shared JWT issuance/verification.

Every service (not just auth-service) can independently verify an access
token using the shared HS256 secret -- no network round-trip to auth-service
or the gateway is required. This is the practical Keycloak-replacement
mechanism: JWT validation is stateless and can happen at the gateway *and*
be re-checked inside each service for defense in depth.

Production upgrade path (documented in SECURITY.md): swap HS256 shared-secret
for RS256 with a JWKS endpoint on auth-service, so services verify with a
public key instead of holding the signing secret.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Literal

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

Role = Literal["risk_officer", "compliance_manager", "ciso", "admin"]
ALL_ROLES: tuple[Role, ...] = ("risk_officer", "compliance_manager", "ciso", "admin")

ALGORITHM = "HS256"


def _secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET environment variable is not set")
    return secret


@dataclass(frozen=True)
class TokenPayload:
    sub: str
    role: Role
    mfa_verified: bool
    exp: int
    iat: int


def create_access_token(*, subject: str, role: Role, mfa_verified: bool, ttl_minutes: int) -> str:
    now = int(time.time())
    claims = {
        "sub": subject,
        "role": role,
        "mfa_verified": mfa_verified,
        "iat": now,
        "exp": now + ttl_minutes * 60,
        "type": "access",
    }
    return jwt.encode(claims, _secret(), algorithm=ALGORITHM)


def create_mfa_bridge_token(*, subject: str, ttl_seconds: int = 300) -> str:
    """Short-lived token proving password-verified-but-not-yet-MFA-verified state."""
    now = int(time.time())
    claims = {"sub": subject, "iat": now, "exp": now + ttl_seconds, "type": "mfa_bridge"}
    return jwt.encode(claims, _secret(), algorithm=ALGORITHM)


def decode_token(token: str, *, expected_type: str = "access") -> dict:
    try:
        claims = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token") from exc
    if claims.get("type") != expected_type:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")
    return claims


_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> TokenPayload:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    claims = decode_token(credentials.credentials, expected_type="access")
    return TokenPayload(
        sub=claims["sub"],
        role=claims["role"],
        mfa_verified=claims.get("mfa_verified", False),
        exp=claims["exp"],
        iat=claims["iat"],
    )


def require_role(*allowed_roles: Role):
    """FastAPI dependency factory: `Depends(require_role("admin", "ciso"))`."""

    def _checker(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if user.role not in allowed_roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Role '{user.role}' is not permitted to perform this action",
            )
        return user

    return _checker
