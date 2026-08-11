from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services import lifecycle


def test_state_machine_forward_transitions():
    assert lifecycle.can_transition("open", "investigating")
    assert lifecycle.can_transition("investigating", "contained")
    assert lifecycle.can_transition("contained", "resolved")
    assert lifecycle.can_transition("resolved", "closed")


def test_state_machine_illegal_transitions():
    # Cannot skip back to open, and closed is terminal.
    assert not lifecycle.can_transition("investigating", "open")
    assert not lifecycle.can_transition("closed", "investigating")
    assert not lifecycle.can_transition("closed", "resolved")


def test_state_machine_reopen_allowed():
    # A recurred finding can be reopened from resolved/contained.
    assert lifecycle.can_transition("resolved", "investigating")
    assert lifecycle.can_transition("contained", "investigating")


def test_severity_rank_ordering():
    assert (
        lifecycle.severity_rank("Critical")
        > lifecycle.severity_rank("High")
        > lifecycle.severity_rank("Medium")
        > lifecycle.severity_rank("Low")
    )
    assert lifecycle.severity_rank("nonsense") == 0


def test_auto_open_threshold_high_and_above():
    assert lifecycle.meets_auto_open_threshold("Critical")
    assert lifecycle.meets_auto_open_threshold("High")
    assert not lifecycle.meets_auto_open_threshold("Medium")
    assert not lifecycle.meets_auto_open_threshold("Low")


def test_sla_window_hours_per_severity():
    assert lifecycle.sla_window_hours("Critical") == 24
    assert lifecycle.sla_window_hours("High") == 72
    assert lifecycle.sla_window_hours("Medium") == 168
    assert lifecycle.sla_window_hours("Low") == 336
    # Unknown severity falls back to the medium window.
    assert lifecycle.sla_window_hours("???") == 168


def test_sla_due_at_adds_window():
    opened = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert lifecycle.sla_due_at(opened, "Critical") == opened + timedelta(hours=24)


def test_is_sla_breached_active_past_due():
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    due = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert lifecycle.is_sla_breached(due, "investigating", now=now)


def test_is_sla_breached_false_when_resolved_or_closed():
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    due = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert not lifecycle.is_sla_breached(due, "resolved", now=now)
    assert not lifecycle.is_sla_breached(due, "closed", now=now)


def test_is_sla_breached_tolerates_naive_datetime():
    now = datetime(2026, 1, 2, tzinfo=timezone.utc)
    naive_due = datetime(2026, 1, 1)  # no tzinfo (as SQLite hands back)
    assert lifecycle.is_sla_breached(naive_due, "open", now=now)


def test_category_for_alert_type_mapping():
    assert lifecycle.category_for_alert_type("THREAT_INTEL_MATCH") == "THREAT_INTEL"
    assert lifecycle.category_for_alert_type("CRITICAL_CVE") == "VULNERABILITY"
    assert lifecycle.category_for_alert_type("COMPLIANCE_GAP") == "COMPLIANCE"
    assert lifecycle.category_for_alert_type("RISK_ANOMALY") == "RISK"
    assert lifecycle.category_for_alert_type("POSTURE_DRIFT") == "SECURITY_POSTURE"
    # Unknown alert types default to security posture.
    assert lifecycle.category_for_alert_type("something_new") == "SECURITY_POSTURE"


def test_category_implies_data_breach():
    assert lifecycle.category_implies_data_breach("DATA_BREACH")
    assert not lifecycle.category_implies_data_breach("SECURITY_POSTURE")
