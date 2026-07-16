from __future__ import annotations

import pytest
from fastapi import HTTPException
from sc_tpcrs_common.jwt_shared import (
    TokenPayload,
    create_access_token,
    create_mfa_bridge_token,
    decode_token,
    require_role,
)


def test_access_token_roundtrip():
    token = create_access_token(subject="user@example.com", role="admin", mfa_verified=True, ttl_minutes=15)
    claims = decode_token(token, expected_type="access")
    assert claims["sub"] == "user@example.com"
    assert claims["role"] == "admin"
    assert claims["mfa_verified"] is True


def test_mfa_bridge_token_roundtrip():
    token = create_mfa_bridge_token(subject="user@example.com", ttl_seconds=60)
    claims = decode_token(token, expected_type="mfa_bridge")
    assert claims["sub"] == "user@example.com"


def test_decode_token_wrong_type_rejected():
    token = create_mfa_bridge_token(subject="user@example.com")
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token, expected_type="access")
    assert exc_info.value.status_code == 401


def test_decode_token_expired_rejected():
    token = create_access_token(subject="user@example.com", role="admin", mfa_verified=True, ttl_minutes=-1)
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token, expected_type="access")
    assert exc_info.value.status_code == 401


def test_decode_token_garbage_rejected():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("not-a-real-token", expected_type="access")
    assert exc_info.value.status_code == 401


def test_require_role_allows_permitted_role():
    checker = require_role("admin", "ciso")
    user = TokenPayload(sub="x", role="admin", mfa_verified=True, exp=0, iat=0)
    assert checker(user=user) is user


def test_require_role_rejects_other_role():
    checker = require_role("admin")
    user = TokenPayload(sub="x", role="risk_officer", mfa_verified=True, exp=0, iat=0)
    with pytest.raises(HTTPException) as exc_info:
        checker(user=user)
    assert exc_info.value.status_code == 403
