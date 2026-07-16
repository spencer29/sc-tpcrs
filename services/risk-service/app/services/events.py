from __future__ import annotations

import logging

from sc_tpcrs_common.kafka_base import KafkaEventConsumer, KafkaEventProducer
from sc_tpcrs_common.kafka_topics import RISK_ANOMALY_ALERTS, RISK_SCORE_UPDATES, VENDOR_LIFECYCLE_EVENTS

from ..config import settings
from ..db import SessionLocal
from .vrs_calculator import compute_for_vendor

logger = logging.getLogger("risk-service.events")

_producer = KafkaEventProducer(bootstrap_servers=settings.kafka_bootstrap_servers, client_id="risk-service")

# Vendor lifecycle states that warrant a fresh VRS computation.
TRIGGER_STATES = {"QUESTIONNAIRE_COMPLETED", "ASSESSMENT_IN_PROGRESS", "ONBOARDED"}


async def handle_vendor_lifecycle_event(event: dict) -> None:
    """Idempotent: always inserts a fresh risk_score_history row, so
    at-least-once Kafka delivery (see kafka_base.py) is safe to replay."""
    payload = event.get("payload", {})
    to_state = payload.get("to_state")
    vendor_id = payload.get("vendor_id")
    if to_state not in TRIGGER_STATES or not vendor_id:
        return

    async with SessionLocal() as db:
        row, anomaly = await compute_for_vendor(db, vendor_id)
        await db.commit()

        await _producer.publish(
            RISK_SCORE_UPDATES,
            "risk.score.updated",
            {"vendor_id": vendor_id, "vrs_score": float(row.vrs_score), "tier": row.tier},
            key=vendor_id,
        )

        if anomaly is not None and anomaly.is_anomalous:
            await _producer.publish(
                RISK_ANOMALY_ALERTS,
                "risk.anomaly.detected",
                {"vendor_id": vendor_id, "anomaly_score": float(anomaly.anomaly_score)},
                key=vendor_id,
            )


def build_consumer() -> KafkaEventConsumer:
    return KafkaEventConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id="risk-service",
        topics=[VENDOR_LIFECYCLE_EVENTS],
        handler=handle_vendor_lifecycle_event,
    )
