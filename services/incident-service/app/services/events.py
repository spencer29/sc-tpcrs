"""Kafka wiring for incident-service.

Consumes MONITORING_ALERTS (the aggregation hub monitoring-service publishes to)
and auto-opens an incident for any alert at/above the configured severity
threshold, deduplicated on the alert id so a re-published alert never spawns a
duplicate incident. Publishes INCIDENT_EVENTS on open and status change so
downstream consumers (dashboards, notifiers) can react.

Fail-soft: the shared producer/consumer no-op when no broker is reachable, so
unit tests and offline demos need no Kafka.
"""

from __future__ import annotations

import logging

from sc_tpcrs_common.kafka_base import KafkaEventConsumer, KafkaEventProducer
from sc_tpcrs_common.kafka_topics import INCIDENT_EVENTS, MONITORING_ALERTS

from ..config import settings
from ..db import SessionLocal
from ..models import Incident
from . import incident_service, lifecycle

logger = logging.getLogger("incident-service.events")

_producer = KafkaEventProducer(bootstrap_servers=settings.kafka_bootstrap_servers, client_id="incident-service")

_CONSUMED_TOPICS = [MONITORING_ALERTS]


async def publish_incident_event(incident: Incident, event_type: str) -> bool:
    return await _producer.publish(
        INCIDENT_EVENTS,
        event_type,
        {
            "incident_id": str(incident.id),
            "reference": incident.reference,
            "vendor_id": str(incident.vendor_id),
            "severity": incident.severity,
            "status": incident.status,
            "category": incident.category,
            "source_ref": incident.source_ref,
        },
        key=str(incident.vendor_id),
    )


async def _handle_monitoring_alert(event: dict) -> None:
    payload = event.get("payload", {})
    vendor_id = payload.get("vendor_id")
    alert_id = payload.get("alert_id")
    severity = payload.get("severity", "Medium")
    if not vendor_id or not alert_id:
        return
    if not lifecycle.meets_auto_open_threshold(severity):
        return

    async with SessionLocal() as db:
        # Dedup: one incident per originating alert.
        existing = await incident_service.find_by_source_ref(db, str(alert_id))
        if existing is not None:
            return
        alert_type = payload.get("alert_type", "")
        incident = await incident_service.create_incident(
            db,
            actor="system:incident-events",
            vendor_id=str(vendor_id),
            title=payload.get("title") or f"{severity} monitoring alert",
            description=f"Auto-opened from monitoring alert {alert_id} ({alert_type}).",
            severity=severity,
            category=lifecycle.category_for_alert_type(alert_type),
            source=MONITORING_ALERTS,
            source_ref=str(alert_id),
        )
        await db.commit()
        await db.refresh(incident)
        await publish_incident_event(incident, "incident.opened")
        logger.info("Auto-opened %s from alert %s (%s)", incident.reference, alert_id, severity)


async def handle_event(event: dict) -> None:
    event_type = event.get("event_type", "")
    if event_type.startswith("monitoring.alert"):
        await _handle_monitoring_alert(event)


def build_consumer() -> KafkaEventConsumer:
    return KafkaEventConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="incident-service",
        topics=_CONSUMED_TOPICS,
        handler=handle_event,
    )
