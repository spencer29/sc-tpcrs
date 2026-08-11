"""Incident lifecycle policy: state machine, SLA windows, severity gating,
and alert->incident mapping. Pure functions (no DB / no I/O) so the rules are
unit-testable in isolation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ..config import settings

# --- Lifecycle state machine ---
STATUSES = ("open", "investigating", "contained", "resolved", "closed")

# Allowed forward (and limited backward) transitions. Reopening a resolved
# incident back to investigating is permitted (the finding recurred); a closed
# incident is terminal.
_TRANSITIONS: dict[str, set[str]] = {
    "open": {"investigating", "contained", "resolved", "closed"},
    "investigating": {"contained", "resolved", "closed"},
    "contained": {"resolved", "investigating", "closed"},
    "resolved": {"closed", "investigating"},
    "closed": set(),
}


def can_transition(current: str, target: str) -> bool:
    return target in _TRANSITIONS.get(current, set())


# --- Severity ordering / gating ---
_SEVERITY_ORDER = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}


def severity_rank(sev: str) -> int:
    return _SEVERITY_ORDER.get(sev, 0)


def meets_auto_open_threshold(severity: str) -> bool:
    return severity_rank(severity) >= severity_rank(settings.auto_open_min_severity)


# --- SLA ---
_SLA_HOURS = {
    "Critical": lambda: settings.sla_hours_critical,
    "High": lambda: settings.sla_hours_high,
    "Medium": lambda: settings.sla_hours_medium,
    "Low": lambda: settings.sla_hours_low,
}


def sla_window_hours(severity: str) -> int:
    return _SLA_HOURS.get(severity, _SLA_HOURS["Medium"])()


def sla_due_at(opened_at: datetime, severity: str) -> datetime:
    return opened_at + timedelta(hours=sla_window_hours(severity))


def is_sla_breached(sla_due: datetime, status: str, *, now: datetime | None = None) -> bool:
    """An incident breaches SLA if it passes its due time while still active
    (not resolved or closed)."""
    if status in ("resolved", "closed"):
        return False
    current = now or datetime.now(timezone.utc)
    # Tolerate naive datetimes coming back from SQLite in tests.
    if sla_due.tzinfo is None:
        sla_due = sla_due.replace(tzinfo=timezone.utc)
    return current > sla_due


# --- Alert -> incident category mapping ---
# monitoring alert_type -> incident category. Anything unmapped is SECURITY_POSTURE.
_ALERT_CATEGORY = {
    "POSTURE_DRIFT": "SECURITY_POSTURE",
    "NEW_EXPOSED_SERVICE": "SECURITY_POSTURE",
    "THREAT_INTEL_MATCH": "THREAT_INTEL",
    "CRITICAL_CVE": "VULNERABILITY",
    "COMPLIANCE_GAP": "COMPLIANCE",
    "RISK_ANOMALY": "RISK",
}


def category_for_alert_type(alert_type: str) -> str:
    return _ALERT_CATEGORY.get(alert_type, "SECURITY_POSTURE")


def category_implies_data_breach(category: str) -> bool:
    return category == "DATA_BREACH"
