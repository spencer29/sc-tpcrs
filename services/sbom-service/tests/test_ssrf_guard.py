from __future__ import annotations

import app.services.ssrf_guard as guard
from app.config import settings


def test_fetching_disabled_by_default():
    # conftest does not enable fetching; default policy is deny-all.
    allowed, reason = guard.is_ref_fetchable("https://example.com/a.json")
    assert allowed is False
    assert "disabled" in reason


def test_non_web_scheme_rejected(monkeypatch):
    monkeypatch.setattr(settings, "sbom_fetch_external_refs", True)
    monkeypatch.setattr(settings, "sbom_ref_allowed_hosts", "example.com")
    allowed, reason = guard.is_ref_fetchable("file:///etc/passwd")
    assert allowed is False
    assert "scheme" in reason


def test_host_not_in_allowlist_rejected(monkeypatch):
    monkeypatch.setattr(settings, "sbom_fetch_external_refs", True)
    monkeypatch.setattr(settings, "sbom_ref_allowed_hosts", "trusted.example.com")
    allowed, reason = guard.is_ref_fetchable("https://evil.example.net/x")
    assert allowed is False
    assert "allow-list" in reason


def test_loopback_rejected_even_if_allowlisted(monkeypatch):
    monkeypatch.setattr(settings, "sbom_fetch_external_refs", True)
    monkeypatch.setattr(settings, "sbom_ref_allowed_hosts", "localhost")
    # Force resolution to loopback regardless of DNS.
    monkeypatch.setattr(guard, "_is_disallowed_ip", lambda host: True)
    allowed, reason = guard.is_ref_fetchable("https://localhost/admin")
    assert allowed is False
    assert "private/loopback/reserved" in reason


def test_allowlisted_public_host_permitted(monkeypatch):
    monkeypatch.setattr(settings, "sbom_fetch_external_refs", True)
    monkeypatch.setattr(settings, "sbom_ref_allowed_hosts", "cdn.example.com")
    monkeypatch.setattr(guard, "_is_disallowed_ip", lambda host: False)
    allowed, reason = guard.is_ref_fetchable("https://cdn.example.com/sbom.json")
    assert allowed is True
    assert reason == "ok"
