"""Kafka wiring for monitoring-service.

Consumes the alert-worthy events emitted by the other modules -- critical CVEs
(sbom-service), non-compliant assessments (compliance-service), and risk
anomalies (risk-service) -- and turns each into a deduplicated MonitoringAlert.
Publishes every opened/changed alert to MONITORING_ALERTS so incident-service
(Module 6) can open incidents.

Fail-soft: the shared KafkaEventProducer/Consumer no-op when no broker is
reachable, so unit tests and offline demos need no Kafka.
"""

from __future__ import annotations

import logging

from sc_tpcrs_common.kafka_base import KafkaEventConsumer, KafkaEventProducer
from sc_tpcrs_common.kafka_topics import (
    COMPLIANCE_ASSESSMENT_EVENTS,
    CVE_ALERTS,
    MONITORING_ALERTS,
    RISK_ANOMALY_ALERTS,
)

from ..config import settings
from ..db import SessionLocal
from ..models import MonitoringAlert
from . import alert_engine
from .audit import record_audit_event

logger = logging.getLogger("monitoring-service.events")

_producer = KafkaEventProducer(bootstrap_servers=settings.kafka_bootstrap_servers, client_id="monitoring-service")

# Topics whose events monitoring reacts to. group_id is stable so restarts
# resume from the last committed offset.
_CONSUMED_TOPICS = [CVE_ALERTS, COMPLIANCE_ASSESSMENT_EVENTS, RISK_ANOMALY_ALERTS]


async def publish_alert(alert: MonitoringAlert) -> bool:
    return await _producer.publish(
        MONITORING_ALERTS,
        "monitoring.alert.raised",
        {
            "alert_id": str(alert.id),
            "vendor_id": str(alert.vendor_id),
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "status": alert.status,
        },
        key=str(alert.vendor_id),
    )


async def publish_alerts(alerts: list[MonitoringAlert]) -> None:
    for alert in alerts:
        if not alert.published:
            ok = await publish_alert(alert)
            alert.published = ok


async def _handle_event(topic_hint: str, event: dict) -> None:
    spec = alert_engine.alert_from_event(topic_hint, event)
    if spec is None:
        return
    async with SessionLocal() as db:
        alert, created = await alert_engine.upsert_alert(db, spec)
        await record_audit_event(
            db,
            actor="system:monitoring-events",
            action="ALERT_RAISED" if created else "ALERT_UPDATED",
            resource=f"vendor:{spec.vendor_id}",
            details={"alert_type": spec.alert_type, "severity": spec.severity, "source": spec.source},
        )
        await db.commit()
        await db.refresh(alert)
        ok = await publish_alert(alert)
        if ok:
            alert.published = True
            await db.commit()


# The shared consumer dispatches by a single handler; we can't see the topic
# from the envelope alone, so alert_from_event inspects event_type too. We pass
# a hint derived from event_type.
async def handle_event(event: dict) -> None:
    event_type = event.get("event_type", "")
    if event_type.startswith("cve."):
        topic_hint = CVE_ALERTS
    elif event_type.startswith("compliance."):
        topic_hint = COMPLIANCE_ASSESSMENT_EVENTS
    elif event_type.startswith("risk.anomaly"):
        topic_hint = RISK_ANOMALY_ALERTS
    else:
        topic_hint = event_type
    await _handle_event(topic_hint, event)


def build_consumer() -> KafkaEventConsumer:
    return KafkaEventConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="monitoring-service",
        topics=_CONSUMED_TOPICS,
        handler=handle_event,
    )
