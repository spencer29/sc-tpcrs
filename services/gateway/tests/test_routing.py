from __future__ import annotations

from app.routing import is_public, resolve_upstream


def test_resolve_upstream_known_prefix():
    resolved = resolve_upstream("vendors/123")
    assert resolved is not None
    base_url, prefix = resolved
    assert prefix == "vendors"


def test_resolve_upstream_unknown_prefix_returns_none():
    assert resolve_upstream("nope/thing") is None


def test_is_public_login_and_mfa_verify():
    assert is_public("auth/login") is True
    assert is_public("auth/mfa/verify") is True


def test_is_public_dev_endpoints():
    assert is_public("auth/dev/mfa-code") is True
    assert is_public("auth/dev/seed-users") is True


def test_is_public_false_for_protected_paths():
    assert is_public("vendors") is False
    assert is_public("auth/me") is False
