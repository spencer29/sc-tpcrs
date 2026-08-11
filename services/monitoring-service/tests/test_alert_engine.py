"""Alert generation, event mapping, and dedup/upsert lifecycle."""

from __future__ import annotations

import uuid

import pytest

from app.services import alert_engine
from app.services.posture import PostureReading


def _reading(
    *,
    posture_score: float = 80.0,
    open_services: list[str] | None = None,
    ioc: int = 0,
    abuse: int = 0,
    exposure: float = 12.0,
) -> PostureReading:
    return PostureReading(
        posture_score=posture_score,
        open_services=open_services or ["https"],
        ioc_match_count=ioc,
        abuse_report_count=abuse,
        exposure_index=exposure,
        raw={},
    )


# --- evaluate_snapshot ---
def test_no_alerts_on_first_snapshot_of_healthy_vendor():
    specs = alert_engine.evaluate_snapshot(
        str(uuid.uuid4()),
        _reading(),
        previous_exposure=None,
        previous_services=None,
    )
    assert specs == []


def test_drift_above_critical_threshold_raises_critical_alert():
    vid = str(uuid.uuid4())
    # exposure jumps by 25 (> critical 20).
    specs = alert_engine.evaluate_snapshot(
        vid,
        _reading(exposure=45.0),
        previous_exposure=20.0,
        previous_services=["https"],
    )
    drift_alerts = [s for s in specs if s.alert_type == alert_engine.POSTURE_DRIFT]
    assert len(drift_alerts) == 1
    assert drift_alerts[0].severity == "Critical"


def test_drift_in_warning_band_raises_high_alert():
    specs = alert_engine.evaluate_snapshot(
        str(uuid.uuid4()),
        _reading(exposure=30.0),
        previous_exposure=20.0,  # +10 -> warning band (>=8, <20)
        previous_services=["https"],
    )
    drift = [s for s in specs if s.alert_type == alert_engine.POSTURE_DRIFT]
    assert len(drift) == 1
    assert drift[0].severity == "High"


def test_small_drift_produces_no_alert():
    specs = alert_engine.evaluate_snapshot(
        str(uuid.uuid4()),
        _reading(exposure=23.0),
        previous_exposure=20.0,  # +3 < warning
        previous_services=["https"],
    )
    assert [s for s in specs if s.alert_type == alert_engine.POSTURE_DRIFT] == []


def test_newly_exposed_sensitive_service_raises_alert():
    specs = alert_engine.evaluate_snapshot(
        str(uuid.uuid4()),
        _reading(open_services=["https", "rdp"], exposure=12.0),
        previous_exposure=12.0,
        previous_services=["https"],
    )
    svc_alerts = [s for s in specs if s.alert_type == alert_engine.NEW_EXPOSED_SERVICE]
    assert len(svc_alerts) == 1
    assert "rdp" in svc_alerts[0].dedup_key


def test_already_exposed_service_does_not_realert():
    specs = alert_engine.evaluate_snapshot(
        str(uuid.uuid4()),
        _reading(open_services=["https", "rdp"], exposure=12.0),
        previous_exposure=12.0,
        previous_services=["https", "rdp"],  # rdp was already there
    )
    assert [s for s in specs if s.alert_type == alert_engine.NEW_EXPOSED_SERVICE] == []


def test_ioc_matches_raise_threat_intel_alert_with_scaled_severity():
    low = alert_engine.evaluate_snapshot(
        str(uuid.uuid4()), _reading(ioc=1), previous_exposure=None, previous_services=None
    )
    high = alert_engine.evaluate_snapshot(
        str(uuid.uuid4()), _reading(ioc=3), previous_exposure=None, previous_services=None
    )
    low_ti = [s for s in low if s.alert_type == alert_engine.THREAT_INTEL_MATCH]
    high_ti = [s for s in high if s.alert_type == alert_engine.THREAT_INTEL_MATCH]
    assert low_ti[0].severity == "Medium"
    assert high_ti[0].severity == "High"


# --- alert_from_event ---
def test_alert_from_cve_event():
    vid = str(uuid.uuid4())
    spec = alert_engine.alert_from_event(
        "sbom.cve.alerts",
        {"event_type": "cve.critical", "payload": {"vendor_id": vid, "cve_id": "CVE-2026-0001"}},
    )
    assert spec is not None
    assert spec.alert_type == alert_engine.CRITICAL_CVE
    assert spec.severity == "Critical"
    assert "CVE-2026-0001" in spec.dedup_key


def test_alert_from_compliance_event_non_compliant():
    vid = str(uuid.uuid4())
    spec = alert_engine.alert_from_event(
        "compliance.assessment.events",
        {
            "event_type": "compliance.assessed",
            "payload": {"vendor_id": vid, "status": "Non-Compliant", "framework": "PCI DSS", "critical_gap_count": 2},
        },
    )
    assert spec is not None
    assert spec.alert_type == alert_engine.COMPLIANCE_GAP
    assert spec.severity == "High"


def test_alert_from_compliant_assessment_is_ignored():
    vid = str(uuid.uuid4())
    spec = alert_engine.alert_from_event(
        "compliance.assessment.events",
        {
            "event_type": "compliance.assessed",
            "payload": {"vendor_id": vid, "status": "Compliant", "critical_gap_count": 0},
        },
    )
    assert spec is None


def test_alert_from_risk_anomaly_event():
    vid = str(uuid.uuid4())
    spec = alert_engine.alert_from_event(
        "risk.anomaly.alerts",
        {"event_type": "risk.anomaly.detected", "payload": {"vendor_id": vid}},
    )
    assert spec is not None
    assert spec.alert_type == alert_engine.RISK_ANOMALY


def test_alert_from_event_without_vendor_is_none():
    assert alert_engine.alert_from_event("cve.alerts", {"event_type": "cve.x", "payload": {}}) is None


# --- upsert_alert dedup ---
async def test_upsert_dedups_open_alerts(db_session):
    vid = str(uuid.uuid4())
    spec = alert_engine.AlertSpec(
        vendor_id=vid,
        alert_type=alert_engine.POSTURE_DRIFT,
        severity="High",
        title="drift",
        description="d",
        dedup_key=alert_engine.POSTURE_DRIFT,
    )
    a1, created1 = await alert_engine.upsert_alert(db_session, spec)
    a2, created2 = await alert_engine.upsert_alert(db_session, spec)
    await db_session.commit()
    assert created1 is True
    assert created2 is False
    assert a1.id == a2.id
    assert a2.occurrence_count == 2


async def test_upsert_escalates_severity(db_session):
    vid = str(uuid.uuid4())
    base = alert_engine.AlertSpec(
        vendor_id=vid,
        alert_type=alert_engine.POSTURE_DRIFT,
        severity="High",
        title="drift high",
        description="d",
        dedup_key=alert_engine.POSTURE_DRIFT,
    )
    worse = alert_engine.AlertSpec(
        vendor_id=vid,
        alert_type=alert_engine.POSTURE_DRIFT,
        severity="Critical",
        title="drift critical",
        description="d",
        dedup_key=alert_engine.POSTURE_DRIFT,
    )
    await alert_engine.upsert_alert(db_session, base)
    a2, created = await alert_engine.upsert_alert(db_session, worse)
    await db_session.commit()
    assert created is False
    assert a2.severity == "Critical"


async def test_resolved_alert_recurrence_opens_new_row(db_session):
    vid = str(uuid.uuid4())
    spec = alert_engine.AlertSpec(
        vendor_id=vid,
        alert_type=alert_engine.POSTURE_DRIFT,
        severity="High",
        title="drift",
        description="d",
        dedup_key=alert_engine.POSTURE_DRIFT,
    )
    a1, _ = await alert_engine.upsert_alert(db_session, spec)
    a1.status = "resolved"
    await db_session.commit()
    a2, created = await alert_engine.upsert_alert(db_session, spec)
    await db_session.commit()
    assert created is True
    assert a2.id != a1.id
