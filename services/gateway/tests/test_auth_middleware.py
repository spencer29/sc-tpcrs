from __future__ import annotations

import pytest
from fastapi import HTTPException
from sc_tpcrs_common.jwt_shared import create_access_token

from app.auth_middleware import authenticate


def test_authenticate_returns_none_without_header():
    assert authenticate(None) is None


def test_authenticate_returns_none_for_non_bearer_scheme():
    assert authenticate("Basic abc123") is None


def test_authenticate_returns_none_for_empty_bearer():
    assert authenticate("Bearer ") is None


def test_authenticate_returns_payload_for_valid_token():
    token = create_access_token(subject="user@example.com", role="admin", mfa_verified=True, ttl_minutes=15)
    payload = authenticate(f"Bearer {token}")
    assert payload is not None
    assert payload.sub == "user@example.com"
    assert payload.role == "admin"


def test_authenticate_raises_for_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        authenticate("Bearer not-a-real-token")
    assert exc_info.value.status_code == 401
