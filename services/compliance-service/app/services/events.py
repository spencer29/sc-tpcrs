"""Kafka wiring for compliance-service.

Consumes VENDOR_LIFECYCLE_EVENTS: when a vendor reaches an onboarding/
assessment state, a baseline compliance assessment is generated automatically
(idempotent -- a fresh append-only assessment row per event, safe to replay
under at-least-once delivery). Publishes COMPLIANCE_ASSESSMENT_EVENTS so
downstream services (monitoring, incident) can react to material gaps.

Fail-soft: KafkaEventProducer/Consumer no-op when no broker is reachable
(see sc_tpcrs_common.kafka_base), so tests and offline demos need no Kafka.
"""

from __future__ import annotations

import logging

from sc_tpcrs_common.kafka_base import KafkaEventConsumer, KafkaEventProducer
from sc_tpcrs_common.kafka_topics import COMPLIANCE_ASSESSMENT_EVENTS, VENDOR_LIFECYCLE_EVENTS

from ..config import settings
from ..db import SessionLocal
from .assessment_service import run_assessment
from .audit import record_audit_event

logger = logging.getLogger("compliance-service.events")

_producer = KafkaEventProducer(bootstrap_servers=settings.kafka_bootstrap_servers, client_id="compliance-service")

# Lifecycle states that warrant a fresh baseline compliance assessment.
TRIGGER_STATES = {"ASSESSMENT_IN_PROGRESS", "ONBOARDED"}


async def publish_assessment_event(assessment) -> bool:
    return await _producer.publish(
        COMPLIANCE_ASSESSMENT_EVENTS,
        "compliance.assessment.completed",
        {
            "vendor_id": str(assessment.vendor_id),
            "framework": assessment.framework,
            "compliance_score": float(assessment.compliance_score),
            "status": assessment.status,
            "critical_gap_count": assessment.critical_gap_count,
        },
        key=str(assessment.vendor_id),
    )


async def handle_vendor_lifecycle_event(event: dict) -> None:
    payload = event.get("payload", {})
    to_state = payload.get("to_state")
    vendor_id = payload.get("vendor_id")
    if to_state not in TRIGGER_STATES or not vendor_id:
        return

    import uuid

    async with SessionLocal() as db:
        assessment = await run_assessment(
            db, vendor_id=uuid.UUID(str(vendor_id)), framework="ALL", actor="system:vendor-lifecycle"
        )
        await record_audit_event(
            db,
            actor="system:vendor-lifecycle",
            action="COMPLIANCE_ASSESSED",
            resource=f"vendor:{vendor_id}",
            details={
                "framework": "ALL",
                "compliance_score": float(assessment.compliance_score),
                "status": assessment.status,
                "trigger_state": to_state,
            },
        )
        await db.commit()
        await publish_assessment_event(assessment)


def build_consumer() -> KafkaEventConsumer:
    return KafkaEventConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="compliance-service",
        topics=[VENDOR_LIFECYCLE_EVENTS],
        handler=handle_vendor_lifecycle_event,
    )
