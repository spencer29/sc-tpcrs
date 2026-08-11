from __future__ import annotations

import uuid

from app.services import events, incident_service

VENDOR = str(uuid.uuid4())


def _alert_event(severity="High", alert_type="THREAT_INTEL_MATCH", alert_id="alert-1", vendor_id=VENDOR):
    return {
        "event_type": "monitoring.alert.raised",
        "payload": {
            "vendor_id": vendor_id,
            "alert_id": alert_id,
            "severity": severity,
            "alert_type": alert_type,
            "title": f"{severity} {alert_type}",
        },
    }


async def test_high_alert_auto_opens_incident(db_session):
    await events.handle_event(_alert_event(severity="High"))
    incidents = await incident_service.all_incidents(db_session)
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.severity == "High"
    assert inc.category == "THREAT_INTEL"
    assert inc.source == "monitoring.alerts"
    assert inc.source_ref == "alert-1"


async def test_medium_alert_does_not_auto_open(db_session):
    await events.handle_event(_alert_event(severity="Medium"))
    incidents = await incident_service.all_incidents(db_session)
    assert incidents == []


async def test_duplicate_alert_deduped(db_session):
    await events.handle_event(_alert_event(alert_id="alert-dup"))
    await events.handle_event(_alert_event(alert_id="alert-dup"))
    incidents = await incident_service.all_incidents(db_session)
    assert len(incidents) == 1


async def test_alert_missing_ids_ignored(db_session):
    await events.handle_event({"event_type": "monitoring.alert.raised", "payload": {"severity": "Critical"}})
    incidents = await incident_service.all_incidents(db_session)
    assert incidents == []


async def test_non_monitoring_event_ignored(db_session):
    await events.handle_event({"event_type": "risk.score.updated", "payload": {"vendor_id": VENDOR}})
    incidents = await incident_service.all_incidents(db_session)
    assert incidents == []


async def test_critical_cve_alert_maps_to_vulnerability(db_session):
    await events.handle_event(_alert_event(severity="Critical", alert_type="CRITICAL_CVE", alert_id="cve-1"))
    incidents = await incident_service.all_incidents(db_session)
    assert incidents[0].category == "VULNERABILITY"
    assert incidents[0].requires_cbn_notification is True  # Critical -> CBN
