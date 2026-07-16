from __future__ import annotations

from sc_tpcrs_common.jwt_shared import TokenPayload, decode_token


def authenticate(authorization_header: str | None) -> TokenPayload | None:
    """Returns TokenPayload for a valid bearer token, or None if no token was
    supplied at all. A *present but invalid/expired* token raises
    HTTPException(401) from `decode_token` -- only a missing header returns
    None, letting the caller decide whether that's acceptable (public path)
    or must 401 (protected path).
    """
    if authorization_header is None or not authorization_header.lower().startswith("bearer "):
        return None
    token = authorization_header.split(" ", 1)[1].strip()
    if not token:
        return None
    claims = decode_token(token, expected_type="access")
    return TokenPayload(
        sub=claims["sub"],
        role=claims["role"],
        mfa_verified=claims.get("mfa_verified", False),
        exp=claims["exp"],
        iat=claims["iat"],
    )
