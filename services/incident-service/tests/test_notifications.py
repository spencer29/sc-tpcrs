from __future__ import annotations

from datetime import datetime, timezone

from app.services import notifications


def _opened():
    return datetime(2026, 8, 4, 9, 0, tzinfo=timezone.utc)


def test_cbn_deadline_is_24h():
    opened = _opened()
    assert (notifications.cbn_deadline(opened) - opened).total_seconds() == 24 * 3600


def test_ndpa_deadline_is_72h():
    opened = _opened()
    assert (notifications.ndpa_deadline(opened) - opened).total_seconds() == 72 * 3600


def test_cbn_notification_content():
    body = notifications.build_cbn_notification(
        reference="INC-000001",
        vendor_name="vendor:abc",
        severity="Critical",
        category="THREAT_INTEL",
        description="C2 beacon observed from vendor infra.",
        opened_at=_opened(),
    )
    assert "CENTRAL BANK OF NIGERIA" in body
    assert "INC-000001" in body
    assert "vendor:abc" in body
    assert "C2 beacon observed" in body
    assert "24h" in body


def test_ndpc_notification_content():
    body = notifications.build_ndpc_notification(
        reference="INC-000002",
        vendor_name="vendor:xyz",
        severity="High",
        description="Customer PII exposed via misconfigured bucket.",
        opened_at=_opened(),
    )
    assert "NIGERIA DATA PROTECTION COMMISSION" in body
    assert "Nigeria Data Protection Act 2023" in body
    assert "INC-000002" in body
    assert "72h" in body


def test_notifications_are_deterministic():
    a = notifications.build_cbn_notification(
        reference="INC-000003", vendor_name="v", severity="High",
        category="RISK", description="d", opened_at=_opened(),
    )
    b = notifications.build_cbn_notification(
        reference="INC-000003", vendor_name="v", severity="High",
        category="RISK", description="d", opened_at=_opened(),
    )
    assert a == b


def test_notification_uses_fallback_when_description_blank():
    body = notifications.build_ndpc_notification(
        reference="INC-000004", vendor_name="v", severity="High",
        description="", opened_at=_opened(),
    )
    assert "potential exposure of personal data" in body
