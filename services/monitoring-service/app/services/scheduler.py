"""In-process periodic sweep scheduler.

A real deployment would drive continuous monitoring from Celery-beat / a cron
sidecar; to keep the prototype self-contained (no extra broker process) the
sweep runs on an asyncio background task started in the FastAPI lifespan. It is
fail-soft and cancellable, mirroring the Kafka consumer's lifecycle. The manual
`POST /monitoring/sweep` endpoint uses the same underlying run_sweep, so the
scheduler is purely a convenience for an always-on stack.
"""

from __future__ import annotations

import asyncio
import logging

from ..config import settings
from ..db import SessionLocal
from . import events, sweep_service

logger = logging.getLogger("monitoring-service.scheduler")


class SweepScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._epoch = 0

    async def _run(self) -> None:
        if settings.sweep_on_startup:
            await asyncio.sleep(settings.sweep_startup_delay_seconds)
            await self._sweep_once()
        while True:
            await asyncio.sleep(settings.sweep_interval_seconds)
            await self._sweep_once()

    async def _sweep_once(self) -> None:
        self._epoch += 1
        try:
            async with SessionLocal() as db:
                result, touched = await sweep_service.run_sweep(
                    db, actor="system:scheduler", sweep_epoch=self._epoch
                )
                await events.publish_alerts(touched)
                await db.commit()
            logger.info(
                "Scheduled sweep #%d: %d snapshots, %d new alerts",
                self._epoch,
                result.snapshots_written,
                result.alerts_opened,
            )
        except Exception:  # noqa: BLE001 - a failed sweep must not kill the scheduler
            logger.exception("Scheduled sweep failed")

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
