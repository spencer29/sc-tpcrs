from __future__ import annotations

from sc_tpcrs_common.kafka_base import KafkaEventProducer
from sc_tpcrs_common.kafka_topics import VENDOR_LIFECYCLE_EVENTS

from ..config import settings

_producer = KafkaEventProducer(bootstrap_servers=settings.kafka_bootstrap_servers, client_id="vendor-service")


async def publish_lifecycle_event(
    *, vendor_id: str, from_state: str, to_state: str, tier: str, actor: str
) -> bool:
    payload = {"vendor_id": vendor_id, "from_state": from_state, "to_state": to_state, "tier": tier, "actor": actor}
    return await _producer.publish(VENDOR_LIFECYCLE_EVENTS, "vendor.lifecycle.transition", payload, key=vendor_id)
