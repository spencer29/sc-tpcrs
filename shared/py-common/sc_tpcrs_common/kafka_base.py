"""Thin async Kafka producer/consumer wrappers used by every service.

Design intent (see project plan, "Kafka choreography flakiness" risk):
Kafka is treated as an *enhancement* on top of synchronous HTTP APIs, never
the only path to a piece of behaviour. These wrappers therefore fail soft:
if the broker is unreachable (e.g. running a single service's unit tests
without docker-compose up), publish() logs and returns rather than raising,
and the consumer loop simply never starts. Handlers registered on the
consumer should be idempotent, since Kafka delivery here is at-least-once.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaError

logger = logging.getLogger("sc_tpcrs_common.kafka")

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


def envelope(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Wrap a payload in a consistent event envelope."""
    return {
        "event_type": event_type,
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }


class KafkaEventProducer:
    """Lazily-connecting producer. Safe to construct even if Kafka is down."""

    def __init__(self, bootstrap_servers: str, client_id: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._client_id = client_id
        self._producer: AIOKafkaProducer | None = None
        self._lock = asyncio.Lock()

    async def _get_producer(self) -> AIOKafkaProducer | None:
        if self._producer is not None:
            return self._producer
        async with self._lock:
            if self._producer is not None:
                return self._producer
            producer = AIOKafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                client_id=self._client_id,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
            try:
                await producer.start()
            except KafkaConnectionError as exc:
                logger.warning("Kafka producer could not connect (%s); publish() will be a no-op.", exc)
                return None
            self._producer = producer
            return self._producer

    async def publish(self, topic: str, event_type: str, payload: dict[str, Any], key: str | None = None) -> bool:
        """Publish an event. Returns True if actually sent, False if Kafka is unavailable."""
        producer = await self._get_producer()
        if producer is None:
            return False
        try:
            await producer.send_and_wait(topic, value=envelope(event_type, payload), key=key)
            return True
        except KafkaError as exc:
            logger.warning("Failed to publish to %s: %s", topic, exc)
            return False

    async def close(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None


class KafkaEventConsumer:
    """Background consumer loop that dispatches to a single async handler.

    Started via `start_background()` from a FastAPI startup event; failures
    to connect are logged, not raised, so a service can still serve its
    synchronous HTTP API even if Kafka is temporarily unavailable.
    """

    def __init__(self, bootstrap_servers: str, group_id: str, topics: list[str], handler: EventHandler) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._group_id = group_id
        self._topics = topics
        self._handler = handler
        self._task: asyncio.Task | None = None
        self._consumer: AIOKafkaConsumer | None = None

    async def _run(self) -> None:
        consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            enable_auto_commit=True,
            auto_offset_reset="earliest",
        )
        try:
            await consumer.start()
        except KafkaConnectionError as exc:
            logger.warning("Kafka consumer (%s) could not connect: %s. Consumer disabled.", self._group_id, exc)
            return
        self._consumer = consumer
        try:
            async for msg in consumer:
                try:
                    await self._handler(msg.value)
                except Exception:  # noqa: BLE001 - one bad event must not kill the loop
                    logger.exception("Error handling Kafka event on topic %s", msg.topic)
        finally:
            await consumer.stop()

    def start_background(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
