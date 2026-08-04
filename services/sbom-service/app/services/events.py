from __future__ import annotations

import logging

from sc_tpcrs_common.kafka_base import KafkaEventProducer
from sc_tpcrs_common.kafka_topics import CVE_ALERTS, SBOM_INGESTION_EVENTS

from ..config import settings

logger = logging.getLogger("sbom-service.events")

_producer = KafkaEventProducer(bootstrap_servers=settings.kafka_bootstrap_servers, client_id="sbom-service")


async def publish_ingestion_event(*, vendor_id: str, document_id: str, component_count: int, vulnerable_count: int) -> None:
    await _producer.publish(
        SBOM_INGESTION_EVENTS,
        "sbom.ingested",
        {
            "vendor_id": vendor_id,
            "document_id": document_id,
            "component_count": component_count,
            "vulnerable_count": vulnerable_count,
        },
        key=vendor_id,
    )


async def publish_cve_alert(*, vendor_id: str, cve_id: str, cvss_score: float | None, severity: str, kev_flag: bool) -> None:
    """Emitted per Critical/KEV CVE found during ingestion. risk-service and a
    future monitoring-service consume cve.alerts to trigger VRS recompute and
    raise priority alerts within one hour (Module 4)."""
    await _producer.publish(
        CVE_ALERTS,
        "cve.detected",
        {
            "vendor_id": vendor_id,
            "cve_id": cve_id,
            "cvss_score": cvss_score,
            "severity": severity,
            "kev_flag": kev_flag,
        },
        key=vendor_id,
    )


async def close() -> None:
    await _producer.close()
